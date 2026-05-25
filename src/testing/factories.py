"""
Gitea test data factories using factory_boy and faker.

Provides reproducible payload generation for API pre-conditions and cleanup
scenarios across unit, integration, and e2e tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import factory
from faker import Faker

from src.api.gitea import build_unique_name

fake = Faker()


class GiteaUserFactory(factory.Factory):
    """Factory for generating Gitea user payloads."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 1)
    username = factory.LazyAttribute(lambda _: fake.user_name())
    full_name = factory.LazyAttribute(lambda _: fake.name())
    login_name = factory.LazyAttribute(lambda obj: obj.username)
    email = factory.LazyAttribute(lambda _: fake.email())
    phone = factory.LazyAttribute(lambda _: fake.phone_number())
    password = factory.LazyFunction(lambda: fake.password(length=16))
    active = True
    created_at = factory.LazyFunction(datetime.utcnow)


class GiteaRepositoryFactory(factory.Factory):
    """Factory for generating Gitea repository payloads."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 1)
    name = factory.LazyFunction(lambda: build_unique_name("repo", "gitea_repository"))
    description = factory.LazyAttribute(lambda _: fake.sentence(nb_words=8))
    private = False
    auto_init = True
    readme = True
    default_branch = "main"


class GiteaIssueFactory(factory.Factory):
    """Factory for generating Gitea issue payloads."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 1)
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=6))
    body = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=3))
    labels = factory.LazyFunction(list)
    assignees = factory.LazyFunction(list)
    milestone = None
    ref = None
    closed = False


class GiteaLabelFactory(factory.Factory):
    """Factory for generating Gitea label payloads."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 1)
    name = factory.LazyFunction(lambda: fake.word())
    description = factory.LazyAttribute(lambda _: fake.sentence(nb_words=4))
    color = factory.LazyFunction(lambda: fake.color()[1:])


class GiteaMilestoneFactory(factory.Factory):
    """Factory for generating Gitea milestone payloads."""

    class Meta:
        model = dict

    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=120))
    deadline = factory.LazyAttribute(lambda _: datetime.utcnow() + timedelta(days=fake.random_int(7, 90)))

