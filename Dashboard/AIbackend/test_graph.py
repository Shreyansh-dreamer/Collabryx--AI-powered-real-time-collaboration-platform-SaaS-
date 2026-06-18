import sys
import os

os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["GROQ-API-KEY"] = "dummy"
os.environ["GOOGLE_CLIENT_ID"] = "dummy"
os.environ["GOOGLE_CLIENT_SECRET"] = "dummy"
os.environ["GOOGLE_REDIRECT_URI"] = "dummy"

from routes.chat import app_graph

try:
    png_bytes = app_graph.get_graph().draw_mermaid_png()
    with open("graph.png", "wb") as f:
        f.write(png_bytes)
    print("Graph image generated successfully as graph.png")
except Exception as e:
    print(f"Error generating graph image: {e}")
    try:
        mermaid_text = app_graph.get_graph().draw_mermaid()
        with open("graph.mermaid", "w") as f:
            f.write(mermaid_text)
        print("Fallback: Saved graph structure in graph.mermaid")
    except Exception as e2:
        print(f"Could not draw mermaid text: {e2}")
