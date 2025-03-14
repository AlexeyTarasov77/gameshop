from unittest.mock import Mock

import tests.utils  # noqa
import pytest
from shopping.repositories import (
    CartSessionManager,
    UserCartManager,
    UserWishlistManager,
    WishlistSessionManager,
    cart_manager_factory,
    wishlist_manager_factory,
)


def test_cart_manager_factory_with_session_key():
    db_mock = Mock()
    cart_manager = cart_manager_factory(db_mock)(session_key="test key")
    assert isinstance(cart_manager, CartSessionManager)


def test_cart_manager_factory_with_user_id():
    db_mock = Mock()
    cart_manager = cart_manager_factory(db_mock)(user_id=1)
    assert isinstance(cart_manager, UserCartManager)


def test_cart_manager_factory_with_both():
    db_mock = Mock()
    cart_manager = cart_manager_factory(db_mock)(user_id=1, session_key="test key")
    assert isinstance(cart_manager, UserCartManager)


def test_cart_manager_factory_with_empty_args():
    db_mock = Mock()
    with pytest.raises(AssertionError):
        cart_manager_factory(db_mock)()


def test_wishlist_manager_factory_with_session_key():
    db_mock = Mock()
    wishlist_manager = wishlist_manager_factory(db_mock)(session_key="test key")
    assert isinstance(wishlist_manager, WishlistSessionManager)


def test_wishlist_manager_factory_with_both():
    db_mock = Mock()
    cart_manager = wishlist_manager_factory(db_mock)(user_id=1, session_key="test key")
    assert isinstance(cart_manager, UserWishlistManager)


def test_wishlist_manager_factory_with_user_id():
    db_mock = Mock()
    wishlist_manager = wishlist_manager_factory(db_mock)(user_id=1)
    assert isinstance(wishlist_manager, UserWishlistManager)


def test_wishlist_manager_factory_with_empty_args():
    db_mock = Mock()
    with pytest.raises(AssertionError):
        wishlist_manager_factory(db_mock)()
