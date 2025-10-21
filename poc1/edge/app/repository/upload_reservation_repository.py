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
    ) -> None:
        db.execute(
            text(
                """
                INSERT INTO upload_reservations
                    (user_id, geohash, geohash_level, latitude, longitude)
                VALUES
                    (:user_id, :geohash, :geohash_level, :latitude, :longitude)
                """
            ),
            {
                "user_id": user_id,
                "geohash": geohash,
                "geohash_level": geohash_level,
                "latitude": latitude,
                "longitude": longitude,
            },
        )
