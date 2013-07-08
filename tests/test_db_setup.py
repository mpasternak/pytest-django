import pytest

from .conftest import create_test_module
from .db_helpers import (mark_exists, mark_database, drop_database, db_exists,
                         skip_if_sqlite)


def test_db_reuse(django_testdir):
    """
    Test the re-use db functionality. This test requires a PostgreSQL server
    to be available and the environment variables PG_HOST, PG_DB, PG_USER to
    be defined.
    """
    skip_if_sqlite()

    create_test_module(django_testdir, '''
import pytest

from .app.models import Item

@pytest.mark.django_db
def test_db_can_be_accessed():
    assert Item.objects.count() == 0
''')

    # Use --create-db on the first run to make sure we are not just re-using a
    # database from another test run
    drop_database()
    assert not db_exists()

    # Do not pass in --create-db to make sure it is created when it
    # does not exist
    result_first = django_testdir.runpytest('-v', '--reuse-db')

    result_first.stdout.fnmatch_lines([
        "*test_db_can_be_accessed PASSED*",
    ])

    assert not mark_exists()
    mark_database()
    assert mark_exists()

    result_second = django_testdir.runpytest('-v', '--reuse-db')
    result_second.stdout.fnmatch_lines([
        "*test_db_can_be_accessed PASSED*",
    ])

    # Make sure the database has not been re-created
    assert mark_exists()

    result_third = django_testdir.runpytest('-v', '--reuse-db', '--create-db')
    result_third.stdout.fnmatch_lines([
        "*test_db_can_be_accessed PASSED*",
    ])

    # Make sure the database has been re-created and the mark is gone
    assert not mark_exists()


def test_xdist_db_setup(django_testdir):
    skip_if_sqlite()

    drop_database('gw0')
    drop_database('gw1')

    create_test_module(django_testdir, '''
import pytest

from .app.models import Item

@pytest.mark.django_db
def test_xdist_db_name(settings):
    # Make sure that the database name looks correct
    db_name = settings.DATABASES['default']['NAME']
    assert db_name.endswith('_gw0')

    # Make sure that it is actually possible to query the database
    assert Item.objects.count() == 0

''')

    result = django_testdir.runpytest('-vv', '-n1', '-s')
    result.stdout.fnmatch_lines([
        "*PASSED*test_xdist_db_name*",
    ])

    assert db_exists('gw0')
