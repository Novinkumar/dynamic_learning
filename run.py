from app import create_app

app = create_app()

if __name__ == "__main__":
    # Debugging must be explicitly enabled through the local Flask CLI.
    app.run(host="127.0.0.1", debug=False)
