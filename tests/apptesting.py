from collections import OrderedDict

from bson.objectid import ObjectId

from documentstore import interfaces, exceptions, domain


class Session(interfaces.Session):
    def __init__(self):
        self._documents = InMemoryDocumentStore()
        self._documents_bundles = InMemoryDocumentsBundleStore()
        self._journals = InMemoryJournalStore()
        self._changes = InMemoryChangesDataStore()

    @property
    def documents(self):
        return self._documents

    @property
    def documents_bundles(self):
        return self._documents_bundles

    @property
    def journals(self):
        return self._journals

    @property
    def changes(self):
        return self._changes


class InMemoryDataStore(interfaces.DataStore):
    def __init__(self):
        self._data_store = {}

    def add(self, data):
        id = data.id()
        if id in self._data_store:
            raise exceptions.AlreadyExists()
        else:
            self.update(data)

    def update(self, data):
        _manifest = data.manifest
        id = data.id()
        self._data_store[id] = _manifest

    def fetch(self, id):
        manifest = self._data_store.get(id)
        if manifest:
            return self.DomainClass(manifest=manifest)
        else:
            raise exceptions.DoesNotExist()


class InMemoryDocumentStore(InMemoryDataStore):
    DomainClass = domain.Document


class InMemoryDocumentsBundleStore(InMemoryDataStore):
    DomainClass = domain.DocumentsBundle


class InMemoryJournalStore(InMemoryDataStore):
    DomainClass = domain.Journal


class InMemoryChangesDataStore(interfaces.ChangesDataStore):
    def __init__(self):
        self._timestamps = OrderedDict()  # timestamps -> mudanças
        self._ids = {}  # ids -> mudanças

    def add(self, change: dict):
        change["_id"] = str(change.get("_id") or ObjectId())
        if change["timestamp"] in self._timestamps or change["_id"] in self._ids:
            raise exceptions.AlreadyExists()
        else:
            self._timestamps[change["timestamp"]] = change
            self._ids[change["_id"]] = change

    def filter(self, since: str = "", limit: int = 500):

        return [
            change
            for timestamp, change in self._timestamps.items()
            if timestamp > since
        ][:limit]

    def fetch(self, id: str) -> dict:
        try:
            return self._ids[id]
        except KeyError:
            raise exceptions.DoesNotExist()


class MongoDBCollectionStub:
    def __init__(self):
        self._mongo_store = OrderedDict()

    def insert_one(self, data):
        import pymongo

        if data["_id"] in self._mongo_store:
            raise pymongo.errors.DuplicateKeyError("")
        else:
            self._mongo_store[data["_id"]] = data

    def find(self, query, sort=None, projection=None):
        since = query["_id"]["$gte"]

        first = 0
        for i, change_key in enumerate(self._mongo_store):
            if self._mongo_store[change_key]["_id"] < since:
                continue
            else:
                first = i
                break

        return SliceResultStub(list(self._mongo_store.values())[first:])


class SliceResultStub:
    def __init__(self, data):
        self._data = data

    def limit(self, val):
        return self._data[:val]
