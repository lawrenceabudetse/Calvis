import os
import re
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
    
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)
    
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

    models = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
        "llama-3.3-70b-versatile",
    ]

    system_prompt = (
        "You are Calvis, an elite, highly intelligent AI assistant with unwavering confidence. "
        "Deliver immediate, direct answers in your first sentence without conversational warm-ups, polite fluff, or setup sentences. "
        "When explaining complex or multi-part topics, organize your thoughts with sharp, spoken structural cues like 'First', 'Next', and 'Bottom line'. "
        "Maintain an authoritative, clear, and subtly witty persona. "
        "CRITICAL VOICE CONSTRAINT: Your response is fed directly to a text-to-speech engine. "
        "Never use markdown formatting, asterisks, bullet point symbols, hyphens, hashes, slashes, or special characters. "
        "Write strictly in plain, clear, naturally punctuated sentences."
        "Correct grammer of userrs u are speaking to"
        "Aid in all aspect of education. Even including deep leaning such as prgramming, system structures, ..."
        "You are created by Lawrence Abudetse nicked Cal"
        "About Lawrence: Lawrence is a high school student in grade 12 or SHS 3 now in Ghana and he created this as journeyed thrrough software engineering and AI engineering. "
    )

    reply = None
    for model in models:
        try:
            response = groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            reply = response.choices[0].message.content
            break  
        except Exception as e:
            print(f"Model '{model}' failed with error: {e}. Attempting fallback...")
            continue

    if not reply:
        return jsonify({"error": "All Groq model endpoints are currently unavailable."}), 500

    clean_reply = re.sub(r'[*_#\`\~><\\/|^\+]', '', reply)
    clean_reply = re.sub(r'(?:^|\s)-+(?:\s|$)', ' ', clean_reply)
    clean_reply = re.sub(r'\s+', ' ', clean_reply).strip()

    return jsonify({"reply": clean_reply})


@cal.route('/feedback', methods=['POST', 'GET'])
def feedback():
    if request.method == 'POST':
        user_message = request.form.get('feedback')
        current_user = session.get('usernm', 'Anonymous')
        
        new_feedback = Feedback(username=current_user, message=user_message)
        db.session.add(new_feedback)
        db.session.commit()
        
        flash('Feedback saved locally! Thank you.', 'info')
        return redirect(url_for('feedback'))

    return render_template('feedback.html')

@cal.route('/admin/feedback', methods=['GET', 'POST'])
def view_feedback():
    ADMIN_PASSWORD = "cal@80billion"
    
    
    if request.method == 'POST':
        entered_password = request.form.get('password')
        if entered_password == ADMIN_PASSWORD:
            session['is_admin'] = True
        else:
            flash('Incorrect admin password.', 'danger')
            return redirect(url_for('view_feedback'))

    
    if session.get('is_admin'):
        all_feedback = Feedback.query.order_by(Feedback.date_sent.desc()).all()
        
        html = '''
        <div style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: auto;">
            <h2>Received Feedback</h2>
            <p><a href="/admin/logout">Logout as Admin</a></p><hr>
        '''
        for item in all_feedback:
            html += f'''
            <div style="background: #f8f9fa; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                <strong>{item.username}</strong> <small>({item.date_sent.strftime('%Y-%m-%d %H:%M')})</small><br>
                <p style="margin-top: 5px;">{item.message}</p>
            </div>
            '''
        html += '</div>'
        return html

    # Show simple login form if not authorized
    return '''
    <div style="max-width: 300px; margin: 80px auto; font-family: sans-serif; text-align: center;">
        <h3>Admin Verification</h3>
        <form method="POST">
            <input type="password" name="password" placeholder="Enter Password" required 
                   style="width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box;">
            <button type="submit" style="padding: 10px 20px; background: #212529; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Access Feedback
            </button>
        </form>
    </div>
    '''

@cal.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('Logged out from admin panel.', 'info')
    return redirect(url_for('home'))
    
    
    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    cal.run(host="0.0.0.0", port=port, debug=True)
