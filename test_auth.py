import os
import tempfile

db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")

from app import app, db, User, Todo  # noqa: E402


def login_as(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_todo_isolation_and_auth():
    with app.app_context():
        db.create_all()
        alice = User(google_sub="a", email="a@x.com", name="Alice")
        bob = User(google_sub="b", email="b@x.com", name="Bob")
        db.session.add_all([alice, bob])
        db.session.commit()
        alice_id, bob_id = alice.id, bob.id

    client = app.test_client()

    # anonymous users get redirected home, not a crash
    resp = client.post("/add", data={"title": "nope"})
    assert resp.status_code == 302

    # alice creates a task
    login_as(client, alice_id)
    client.post("/add", data={"title": "Alice task"})
    with app.app_context():
        todo_id = Todo.query.filter_by(title="Alice task").first().id

    # bob can't touch alice's task by guessing its id
    login_as(client, bob_id)
    assert client.get(f"/update/{todo_id}").status_code == 404
    assert client.get(f"/delete/{todo_id}").status_code == 404

    # alice still owns it and can complete it
    login_as(client, alice_id)
    resp = client.get(f"/update/{todo_id}")
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Todo, todo_id).complete is True

    print("ok")


if __name__ == "__main__":
    try:
        test_todo_isolation_and_auth()
    finally:
        os.close(db_fd)
        os.remove(db_path)
