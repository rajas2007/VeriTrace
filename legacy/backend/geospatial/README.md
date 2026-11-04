# UdyogPermit AI Geospatial Module

Drop this `geospatial` directory into `backend/`.

## Dependencies
Merge `requirements.txt` into your backend requirements and install:
`pip install -r requirements.txt`

## API integration
In `main.py`:
```python
from geospatial.engine import GeospatialEngine
from geospatial.schemas import GeospatialAnalysisRequest
geospatial_engine = GeospatialEngine()

@app.post('/api/v1/geospatial/analyze')
async def analyze_geospatial(request: GeospatialAnalysisRequest):
    result = geospatial_engine.analyze(request.latitude, request.longitude, request.radius_m)
    return result.model_dump()
```

## Curl
Windows CMD:
`curl -X POST http://localhost:8000/api/v1/geospatial/analyze -H "Content-Type: application/json" -d "{\"latitude\":19.1234,\"longitude\":73.1234,\"radius_m\":3000}"`

Linux/macOS:
`curl -X POST http://localhost:8000/api/v1/geospatial/analyze -H 'Content-Type: application/json' -d '{"latitude":19.1234,"longitude":73.1234,"radius_m":3000}'`

The module reports spatial evidence only; it does not declare that a legal clearance is required. Regulatory interpretation remains in Agent 2.
