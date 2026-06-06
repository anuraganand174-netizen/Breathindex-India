"""
Flask REST API for AQI India Analyzer.
Run locally: python -m api.flask_api
Production: gunicorn wsgi:app
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from backend.config import config
from backend.db import ping, session_scope
from backend.services import aqi_service, health_service, live_aqi_service, ml_service

_FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["JSON_SORT_KEYS"] = False

    CORS(
        app,
        resources={r"/api/*": {"origins": config.CORS_ORIGINS}},
        supports_credentials=False,
    )

    @app.get("/api/health")
    def health():
        try:
            db_ok = ping()
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "degraded", "database": False, "error": str(exc)}), 503
        return jsonify({
            "status": "ok",
            "database": db_ok,
            "use_sqlite": config.USE_SQLITE,
        })

    @app.get("/api/states")
    def states():
        with session_scope() as session:
            return jsonify({"data": aqi_service.list_states(session)})

    @app.get("/api/cities")
    def cities():
        state_id = request.args.get("state_id", type=int)
        with session_scope() as session:
            return jsonify({"data": aqi_service.list_cities(session, state_id)})

    @app.get("/api/aqi/latest")
    def aqi_latest():
        city_id = request.args.get("city_id", type=int)
        live = request.args.get("live", default="1", type=str) == "1"
        if not city_id:
            return jsonify({"error": "city_id is required"}), 400
        with session_scope() as session:
            if live:
                result = live_aqi_service.get_live_for_city(session, city_id)
                if result.get("ok"):
                    return jsonify({"data": result, "live": not result.get("fallback")})
            row = aqi_service.latest_reading(session, city_id)
        if not row:
            return jsonify({"error": "No readings for this city"}), 404
        return jsonify({"data": row, "live": False})

    @app.get("/api/aqi/live")
    def aqi_live():
        city_id = request.args.get("city_id", type=int)
        force = request.args.get("refresh", default="0", type=str) == "1"
        if not city_id:
            return jsonify({"error": "city_id is required"}), 400
        with session_scope() as session:
            result = live_aqi_service.get_live_for_city(session, city_id, force=force)
        code = 200 if result.get("ok") else 404
        return jsonify(result), code

    @app.get("/api/aqi/live/map")
    def aqi_live_map():
        force = request.args.get("refresh", default="0", type=str) == "1"
        with session_scope() as session:
            payload = live_aqi_service.get_map_data(session, force=force)
        if payload.get("data"):
            payload["summary"] = live_aqi_service.national_summary(payload["data"])
        return jsonify(payload)

    @app.get("/api/aqi/history")
    def aqi_history():
        city_id = request.args.get("city_id", type=int)
        days = request.args.get("days", default=30, type=int)
        if not city_id:
            return jsonify({"error": "city_id is required"}), 400
        with session_scope() as session:
            rows = aqi_service.history(session, city_id, days=days)
        return jsonify({"data": rows, "count": len(rows)})

    @app.get("/api/stats/summary")
    def stats_summary():
        with session_scope() as session:
            return jsonify({"data": aqi_service.summary_stats(session)})

    @app.get("/api/health-impact")
    def health_impact():
        aqi = request.args.get("aqi", type=int)
        with session_scope() as session:
            if aqi is not None:
                row = health_service.impact_for_aqi(session, aqi)
                if not row:
                    return jsonify({"error": "No impact band for this AQI"}), 404
                return jsonify({"data": row})
            return jsonify({"data": health_service.all_impacts(session)})

    @app.get("/api/predict")
    def predict():
        city_id = request.args.get("city_id", type=int)
        model = request.args.get("model", default="random_forest", type=str)
        horizon = request.args.get("horizon", default=7, type=int)
        if not city_id:
            return jsonify({"error": "city_id is required"}), 400
        with session_scope() as session:
            result = ml_service.predict(session, city_id, model_name=model, horizon=horizon)
        code = 200 if result.get("ok") else 404
        return jsonify(result), code

    @app.get("/api/models")
    def models_list():
        return jsonify({"data": ml_service.list_available_models()})

    # Optional: serve frontend when not using GitHub Pages
    @app.get("/")
    def index():
        index_path = _FRONTEND / "index.html"
        if index_path.exists():
            return send_from_directory(_FRONTEND, "index.html")
        return jsonify({"message": "AQI India API", "docs": "/api/health"})

    @app.get("/<path:path>")
    def static_files(path: str):
        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404
        target = _FRONTEND / path
        if target.is_file():
            return send_from_directory(_FRONTEND, path)
        return jsonify({"error": "Not found"}), 404

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5055"))
    app.run(host="0.0.0.0", port=port, debug=config.FLASK_DEBUG)
