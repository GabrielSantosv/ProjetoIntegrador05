from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from fastapi.responses import FileResponse
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

# Mount media files so frontend can preview uploaded PDFs
# MEDIA_ROOT can be set in environment; default to ./media
MEDIA_ROOT = os.getenv('MEDIA_ROOT', './media')
if os.path.isdir(MEDIA_ROOT):
    app.mount('/media', StaticFiles(directory=MEDIA_ROOT), name='media')
else:
    # ensure directory exists so StaticFiles can serve after first upload
    try:
        os.makedirs(MEDIA_ROOT, exist_ok=True)
        app.mount('/media', StaticFiles(directory=MEDIA_ROOT), name='media')
    except Exception:
        # If mount fails, we'll still continue; router endpoints will create folders on upload
        pass


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


@app.get('/_debug_cwd')
def _debug_cwd():
    """Debug endpoint to inspect server working directory and media root"""
    try:
        return {
            'cwd': os.getcwd(),
            'media_root': os.path.abspath(MEDIA_ROOT),
            'media_exists': os.path.isdir(MEDIA_ROOT)
        }
    except Exception as e:
        return {'error': str(e)}


@app.get('/media_proxy/{path:path}')
def _media_proxy(path: str):
    """Serve files directly from MEDIA_ROOT path (fallback when StaticFiles returns 404).
    Use exact disk path after /media_proxy/ — useful for testing Unicode filenames.
    """
    try:
        # normalize and prevent escaping out of MEDIA_ROOT
        safe_path = os.path.normpath(path).lstrip(os.sep)
        file_path = os.path.join(os.path.abspath(MEDIA_ROOT), safe_path)
        if not file_path.startswith(os.path.abspath(MEDIA_ROOT)):
            raise HTTPException(status_code=400, detail='Invalid path')
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail='File not found')
        return FileResponse(file_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
