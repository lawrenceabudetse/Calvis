import io
import os
from datetime import timedelta
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.environ.get("SECRET_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not SECRET_KEY or not GROQ_API_KEY:
    raise RuntimeError("Missing SECRET_KEY or GROQ_API_KEY in environment variables.")


cal = Flask(__name__)
cal.config["SECRET_KEY"] = SECRET_KEY
cal.permanent_session_lifetime = timedelta(minutes=20)
cal.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.sqlite3"
cal.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(cal)
groq_client = Groq(api_key=GROQ_API_KEY)

    
class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)

    def __init__(self, name, email):
        self.name = name
        self.email = email



with cal.app_context():
    db.create_all()


@cal.route("/")
def home():
    return render_template("home_page.html")


@cal.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session.permanent = True
        user_input = request.form["username"]
        session["username"] = user_input

        found_user = users.query.filter_by(name=user_input).first()

        if found_user:
            session["useremail"] = found_user.email
        else:
            usr = users(user_input, None)
            db.session.add(usr)
            db.session.commit()

        flash("Login Successful", "info")
        return redirect(url_for("user"))

    else:
        if "username" in session:
            flash("Already logged in!", "info")
            return redirect(url_for("user"))
        return render_template("login.html")


@cal.route("/user", methods=["POST", "GET"])
def user():
    if "username" in session:
        username = session["username"]
        email = session.get("useremail", None)

        if request.method == "POST":
            email = request.form["useremail"]
            session["useremail"] = email
            found_user = users.query.filter_by(name=username).first()
            if found_user:
                found_user.email = email
                db.session.commit()

        return render_template("user.html", email=email, user=username)
    else:
        flash("Please login now!", "info")
        return redirect(url_for("login"))


@cal.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("useremail", None)
    flash("You have been logged out", "warning")
    return redirect(url_for("login"))


@cal.route("/calvis")
def calvis():
    if "username" not in session:
        flash("Please login to talk to Calvis!", "warning")
        return redirect(url_for("login"))
    return render_template("calvis.html")


@cal.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        
        selected_model = "llama-3.1-8b-instant"

        response = groq_client.chat.completions.create(
            model=selected_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are Calvis, an elite AI assistant in the style of Jarvis. Be concise, witty, and helpful.",
                },
                {"role": "user", "content": user_message},
            ],
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"Error in chat_api: {e}")
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    cal.run(host="0.0.0.0", port=port, debug=True)
