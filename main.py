import uvicorn
import os

def main():
    print("--- 🚀 Starting WebConnect AI Web App ---")
    print("Local URL: http://localhost:8000")
    
    # Run the FastAPI app
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
