from flask import Flask, render_template, request, redirect, session
import json
import os
import hashlib
import smtplib
from email.message import EmailMessage

app = Flask(__name__)

# ==========================================
# SETTINGS
# ==========================================

app.secret_key = "cs2-score-keeper-secret-key"

PLAYERS_FILE = "players.json"

# These are loaded from Windows environment variables.
EMAIL_ADDRESS = os.environ.get("CS2_EMAIL")
EMAIL_PASSWORD = os.environ.get("CS2_EMAIL_PASSWORD")


# ==========================================
# LOAD PLAYERS
# ==========================================

def load_players():

    if not os.path.exists(PLAYERS_FILE):
        return {}

    try:
        with open(
            PLAYERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except json.JSONDecodeError:

        return {}


# ==========================================
# SAVE PLAYERS
# ==========================================

def save_players(players):

    with open(
        PLAYERS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            players,
            file,
            indent=4
        )


# ==========================================
# PASSWORD HASH
# ==========================================

def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()


# ==========================================
# SEND EMAIL
# ==========================================

def send_registration_email(email, username):

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:

        print("Email settings are not configured.")
        return False

    try:

        message = EmailMessage()

        message["Subject"] = "Welcome to CS2 Score Keeper!"

        message["From"] = EMAIL_ADDRESS

        message["To"] = email

        message.set_content(
            f"""
Hello {username}!

Your account on CS2 Score Keeper
has been created successfully.

Username: {username}

You can now log in and start
tracking your CS2 score.

Good luck! 🎮🏆

CS2 Score Keeper
"""
        )

        with smtplib.SMTP(
            "smtp.gmail.com",
            587
        ) as server:

            server.starttls()

            server.login(
                EMAIL_ADDRESS,
                EMAIL_PASSWORD
            )

            server.send_message(message)

        print(
            "Registration email sent to:",
            email
        )

        return True

    except Exception as error:

        print(
            "Email error:",
            error
        )

        return False


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# REGISTER
# ==========================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # Check fields

        if not username or not email or not password:

            return render_template(
                "register.html",
                error="Please complete all fields!"
            )

        players = load_players()

        # Check username

        if username in players:

            return render_template(
                "register.html",
                error="Username already exists!"
            )

        # Check email

        for player in players.values():

            if player.get("email", "").lower() == email.lower():

                return render_template(
                    "register.html",
                    error="This email is already registered!"
                )

        # Create account

        players[username] = {

            "email": email,

            "password": hash_password(
                password
            ),

            "score": 0
        }

        save_players(players)

        # Send confirmation email

        email_sent = send_registration_email(
            email,
            username
        )

        if email_sent:

            print(
                "Account created and email sent."
            )

        else:

            print(
                "Account created, but email could not be sent."
            )

        return redirect("/login")

    return render_template(
        "register.html"
    )


# ==========================================
# LOGIN
# ==========================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        players = load_players()

        if username not in players:

            return render_template(
                "login.html",
                error="Username or password is incorrect!"
            )

        password_hash = hash_password(
            password
        )

        if players[username]["password"] != password_hash:

            return render_template(
                "login.html",
                error="Username or password is incorrect!"
            )

        session["username"] = username

        return redirect("/dashboard")

    return render_template(
        "login.html"
    )


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "username" not in session:

        return redirect("/login")

    username = session["username"]

    players = load_players()

    if username not in players:

        session.clear()

        return redirect("/login")

    score = players[username].get(
        "score",
        0
    )

    email = players[username].get(
        "email",
        ""
    )

    return render_template(
        "dashboard.html",
        username=username,
        email=email,
        score=score
    )


# ==========================================
# ADD SCORE
# ==========================================

@app.route(
    "/add-score",
    methods=["POST"]
)
def add_score():

    if "username" not in session:

        return redirect("/login")

    username = session["username"]

    try:

        points = int(
            request.form.get(
                "points",
                0
            )
        )

    except ValueError:

        return redirect("/dashboard")

    if points <= 0:

        return redirect("/dashboard")

    players = load_players()

    if username in players:

        players[username]["score"] += points

        save_players(players)

    return redirect("/dashboard")


# ==========================================
# REMOVE SCORE
# ==========================================

@app.route(
    "/remove-score",
    methods=["POST"]
)
def remove_score():

    if "username" not in session:

        return redirect("/login")

    username = session["username"]

    try:

        points = int(
            request.form.get(
                "points",
                0
            )
        )

    except ValueError:

        return redirect("/dashboard")

    if points <= 0:

        return redirect("/dashboard")

    players = load_players()

    if username in players:

        players[username]["score"] -= points

        save_players(players)

    return redirect("/dashboard")


# ==========================================
# LEADERBOARD
# ==========================================

@app.route("/leaderboard")
def leaderboard():

    players = load_players()

    leaderboard_data = sorted(
        players.items(),
        key=lambda player:
            player[1].get(
                "score",
                0
            ),
        reverse=True
    )

    return render_template(
        "leaderboard.html",
        players=leaderboard_data
    )


# ==========================================
# DELETE ACCOUNT
# ==========================================

@app.route(
    "/delete-account",
    methods=["POST"]
)
def delete_account():

    if "username" not in session:

        return redirect("/login")

    username = session["username"]

    players = load_players()

    if username in players:

        del players[username]

        save_players(players)

    session.clear()

    return redirect("/")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )