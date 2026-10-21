"""Catalog metadata and catalog-constrained detection identity evidence."""
from alembic import op
import sqlalchemy as sa

revision = "0011_product_identity"
down_revision = "0010_video_job_idempotency"
branch_labels = None
depends_on = None


def _product_columns():
    return (
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("variant", sa.String(100), nullable=True),
        sa.Column("package_size", sa.String(64), nullable=True),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("reference_images", sa.JSON(), nullable=True),
    )


def _detection_columns():
    return (
        sa.Column("identity_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("identity_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("variant", sa.String(100), nullable=True),
        sa.Column("package_size", sa.String(64), nullable=True),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("identity_evidence", sa.JSON(), nullable=True),
    )


def _columns(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _indexes(bind, table):
    return {index["name"] for index in sa.inspect(bind).get_indexes(table)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("products"):
        product_columns = _columns(bind, "products")
        with op.batch_alter_table("products") as batch:
            for column in _product_columns():
                if column.name not in product_columns:
                    batch.add_column(column)
        product_indexes = _indexes(bind, "products")
        for name, columns, unique in (
            ("ix_products_brand", ["brand"], False),
            ("ix_products_category", ["category"], False),
            ("ix_products_barcode", ["barcode"], True),
        ):
            if name not in product_indexes:
                op.create_index(name, "products", columns, unique=unique)

    if inspector.has_table("video_detections"):
        detection_columns = _columns(bind, "video_detections")
        with op.batch_alter_table("video_detections") as batch:
            for column in _detection_columns():
                if column.name not in detection_columns:
                    batch.add_column(column)
        detection_indexes = _indexes(bind, "video_detections")
        for name, columns in (
            ("ix_video_detections_identity_status", ["identity_status"]),
            ("ix_video_detections_category", ["category"]),
        ):
            if name not in detection_indexes:
                op.create_index(name, "video_detections", columns)


def downgrade():
    # Catalog and evidence are intentionally retained on code rollback.
    pass
