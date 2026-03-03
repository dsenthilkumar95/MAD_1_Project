from extensions import login_manager, app
from models import User
from routes import main_bp

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(main_bp)

if __name__ == "__main__":
    app.run(debug=True)
