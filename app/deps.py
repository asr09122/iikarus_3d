from fastapi.middleware.cors import CORSMiddleware

def add_cors(app, origins=None):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
