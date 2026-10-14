"""Create isolated demonstration tables; leave the legacy trial untouched."""
from alembic import op
from app.models import Base

revision = '001_demo'
down_revision = None

def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql': op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    Base.metadata.create_all(bind)

def downgrade():
    raise RuntimeError('Rollback would remove demo records. Back up and obtain explicit deletion approval first.')
