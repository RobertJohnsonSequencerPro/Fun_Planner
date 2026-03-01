"""Web entry point — runs the Flask GUI."""
import webbrowser
import threading
from web import create_app

app = create_app()

if __name__ == "__main__":
    # Auto-open browser after a short delay
    def _open():
        import time; time.sleep(1)
        webbrowser.open("http://127.0.0.1:5000")
    threading.Thread(target=_open, daemon=True).start()

    app.run(host="0.0.0.0", debug=False, port=5000)
