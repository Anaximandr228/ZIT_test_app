import json
from typing import Generator
import psycopg2
import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient
from app import models
from app.config import user, password, host
from app.zit_app import app, get_db

SQLALCHEMY_DATABASE_URL = f'postgresql://{user}:{password}@{host}/test'


@pytest.fixture(scope="session")
def connection():
    con = psycopg2.connect(dbname='postgres',
                           user=user, host=host,
                           password=password)

    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()
    cur.execute('DROP DATABASE IF EXISTS test')
    cur.execute("CREATE DATABASE test")

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
    )
    models.Base.metadata.create_all(bind=engine)
    return engine.connect()


@pytest.fixture(scope="session")
def db_session(connection):
    transaction = connection.begin()
    session_factory = sessionmaker(autocommit=False,
                                   autoflush=False,
                                   bind=connection)
    session = session_factory()
    yield session
    transaction.rollback()


@pytest.fixture(scope='module')
def client(db_session) -> Generator:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def products_setup(db_session):
    db_type = models.ProductType(name='test_type')
    db_session.add(db_type)
    db_session.commit()
    db_product = models.Product(name='Test', product_type_id=1)
    db_session.add(db_product)
    db_session.commit()


def test_get_products(client, products_setup):
    print('test_get_products')
    response = client.get("/products")
    assert response.status_code == 200
    assert response.json()[0]['name'] == 'Test'


def test_get_product_id(client, products_setup):
    print('test_get_products_id')
    response = client.get("/products/1")
    assert response.status_code == 200
    assert response.json()[0]['name'] == 'Test'


def test_get_products_type(client, products_setup):
    print('test_get_products_type')
    response = client.get("/products/type/1")
    assert response.status_code == 200
    assert response.json()[0]['name'] == 'Test'


def test_post_product(client, products_setup, db_session):
    print('test_post_products')
    data = {
        "name": "Test",
        "product_type_id": 1
    }
    response = client.post("/products", data=json.dumps(data))
    saved_product = db_session.query(models.Product).\
        filter(models.Product.id == response.json()['id']).all()
    assert response.status_code == 200
    assert response.json()['name'] == 'Test'
    assert saved_product[0].name == 'Test'


def test_post_product_type(client, products_setup, db_session):
    print('test_post_products')
    data = {
        "name": "test_type"
    }
    response = client.post("/type", data=json.dumps(data))
    saved_product_type = db_session.query(models.ProductType).\
        filter(models.ProductType.id == response.json()['id'])
    assert response.status_code == 200
    assert response.json()['name'] == 'test_type'
    assert saved_product_type[0].name == 'test_type'
