import uvicorn
import os

def main():
    port = int(os.environ.get("PORT", 8000))
    print(f"--- 🚀 Starting WebConnect AI Web App on port {port} ---")
    
    # Run the FastAPI app
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
