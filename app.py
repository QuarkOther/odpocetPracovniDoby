from flask import Flask, render_template

app = Flask(__name__)

# Pracovní doba: 8 hodin 30 minut
WORK_MINUTES = 8 * 60 + 30


@app.route("/")
def index():
    return render_template("index.html", work_minutes=WORK_MINUTES)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=13400, debug=False)
