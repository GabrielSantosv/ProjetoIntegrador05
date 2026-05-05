from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routers import documents, auth

# Create FastAPI app
app = FastAPI(
    title="Extração de Documentos Legais",
    description="API para extração e análise de documentos legais",
    version="1.0.0"
)

# Add CORS middleware BEFORE other middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router)
app.include_router(auth.router)


@app.get('/health')
async def health_check():
    """Health check endpoint - no auth required"""
    return {'status': 'ok', 'message': 'API is running'}


@app.get('/')
async def root():
    """Root endpoint - no auth required"""
    return {
        'message': 'Extração de Documentos Legais API',
        'version': '1.0.0',
        'docs': '/docs'
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
