import click
from utils.migration_manager import MigrationManager

@click.group()
def cli():
    """Утилита для управления миграциями базы данных"""
    pass

@cli.command()
@click.argument('message')
def create(message):
    """Создать новую миграцию"""
    manager = MigrationManager()
    if manager.create_migration(message):
        click.echo("Миграция успешно создана")
    else:
        click.echo("Ошибка при создании миграции")

@cli.command()
@click.option('--revision', default='head', help='Ревизия для обновления')
def upgrade(revision):
    """Обновить базу данных"""
    manager = MigrationManager()
    if manager.upgrade(revision):
        click.echo(f"База данных обновлена до ревизии {revision}")
    else:
        click.echo("Ошибка при обновлении базы данных")

@cli.command()
@click.argument('revision')
def downgrade(revision):
    """Откатить базу данных"""
    manager = MigrationManager()
    if manager.downgrade(revision):
        click.echo(f"База данных откачена до ревизии {revision}")
    else:
        click.echo("Ошибка при откате базы данных")

@cli.command()
def current():
    """Показать текущую ревизию"""
    manager = MigrationManager()
    revision = manager.get_current_revision()
    if revision:
        click.echo(f"Текущая ревизия: {revision}")
    else:
        click.echo("Ошибка при получении текущей ревизии")

if __name__ == '__main__':
    cli() 