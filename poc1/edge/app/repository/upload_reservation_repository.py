from sqlalchemy.orm import Session
from sqlalchemy import text


class UploadReservationRepository:
    """Handles persistence of upload reservations prior to MinIO uploads."""

    def create_reservation(
        self,
        db: Session,
        user_id: int,
        geohash: str,
        geohash_level: int,
        latitude: float,
        longitude: float,
        upload_object_key: str,
    ) -> int:
        result = db.execute(
            text(
                """
                INSERT INTO upload_reservations
                    (user_id, geohash, geohash_level, latitude, longitude, object_key)
                VALUES
                    (:user_id, :geohash, :geohash_level, :latitude, :longitude, :object_key)
                """
            ),
            {
                "user_id": user_id,
                "geohash": geohash,
                "geohash_level": geohash_level,
                "latitude": latitude,
                "longitude": longitude,
                "object_key": upload_object_key,
            },
        )
        return result.lastrowid or db.execute(
            text(
                """
                SELECT id FROM upload_reservations
                WHERE user_id = :user_id AND object_key = :object_key
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id, "object_key": upload_object_key},
        ).scalar_one()
