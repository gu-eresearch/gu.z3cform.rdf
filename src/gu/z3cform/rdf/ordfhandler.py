import transaction
import logging
from transaction.interfaces import ISavepointDataManager, IDataManagerSavepoint
from zope.interface import implements
from ordf.handler import Handler
import threading
from rdflib import Graph
# transaction aware ordf handler

# /Users/gerhard/Downloads/buildout/eggs/alm.solrindex-1.1.1-py2.7.egg/alm/solrindex/index.py
# /Users/gerhard/Downloads/buildout/eggs/collective.indexing-2.0a3-py2.7.egg/collective/indexing/transactions.py
# /Users/gerhard/Downloads/buildout/eggs/p01.fsfile-0.6.0-py2.7.egg/p01/fsfile/storage.py
# /Users/gerhard/Downloads/buildout/eggs/p01.fsfile-0.6.0-py2.7.egg/p01/fsfile/tm.py
# /Users/gerhard/Downloads/buildout/eggs/p01.tmp-0.6.0-py2.7.egg/p01/tmp/file.py
# /Users/gerhard/Downloads/buildout/eggs/z3c.indexer-0.6.0-py2.7.egg/z3c/indexer/interfaces.py
# /Users/gerhard/Downloads/buildout/eggs/zope.sendmail-3.7.5-py2.7.egg/zope/sendmail/delivery.py

LOG = logging.getLogger(__name__)

from ordf.utils import get_identifier

class TransactionAwareHandler(Handler):

    dm = None

    def __init__(self, **kw):
        super(TransactionAwareHandler, self).__init__(**kw)
        self.dm = ORDFDataManager(self)
        LOG.info("Creating new handler")

    def get(self, identifier):
        identifier = get_identifier(identifier)
        result = self.dm.get(identifier)
        if result is None:
            result = super(TransactionAwareHandler, self).get(identifier)
            # dm.put(identifier, result) no need to cache/store a read only graph
            #   we only put stuff, that will be put back to store
        else:
            LOG.info("Handler: Returned cached graph %s", identifier)
        return result

    def put(self, graph):
        if isinstance(graph, Graph):
            contexts = [graph]
        else:
            contexts = graph.contexts()
        for ctx in contexts:
            identifier = get_identifier(ctx)
            self.dm.put(ctx)
        LOG.info("Handler: schedule put(%s)", identifier)

    def append(self, frag):
        graph = self.get(frag.identifier)
        if graph is not None:
            graph += frag
        else:
            graph = frag
        self.put(graph)
        LOG.info("Handler: schedule append(%s, %s)", frag.identifier)
        
    def remove(self, identifier):
        self.dm.remove(identifier)
        LOG.info("Handler: schedule remove(%s)", identifier)

    def _do_put(self, graph):
        super(TransactionAwareHandler, self).put(graph)

    def _do_remove(self, identifier):
        super(TransactionAwareHandler, self).remove(identifier)


class ORDFDataManager(threading.local):

    implements(ISavepointDataManager)

    transaction_manager = transaction.manager

    needs_init = True
    handler = None

    def __init__(self, handler):
        LOG.info("JOIN TRANSACTION: %s", self)
        self.handler = handler

    def _init(self):
        if self.needs_init:
            self.cache = {}
            self.to_remove = []
            transaction.get().join(self)
            self.needs_init = False

    def _reset(self):
        self.needs_init = True
        self.cache = None
        self.to_remove = None
        # transaction.get().unjoin(self) don't do this here ... might cause troubles in 2 phase commit

    def get(self, identifier):
        self._init()
        return self.cache.get(identifier, None)

    def put(self, graph):
        self._init()
        self.cache[graph.identifier] = graph

    def remove(self, identifier):
        self._init()
        self.to_remove.append(identifier)

    def abort(self, transaction):
        LOG.info("TRANSACTION: abort %s", self)
        self.tpc_abort(transaction)
    
    # Two-phase commit protocol.  These methods are called by the ITransaction
    # object associated with the transaction being committed.  The sequence
    # of calls normally follows this regular expression:
    #     tpc_begin commit tpc_vote (tpc_finish | tpc_abort)

    def tpc_begin(self, transaction):
        """Begin commit of a transaction, starting the two-phase commit.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """
        LOG.info("TRANSACTION: tpc_begin %s", self)
        # TODO: prepare whatever is necessary to commit transaction

    def commit(self, transaction):
        """Commit modifications to registered objects.

        Save changes to be made persistent if the transaction commits (if
        tpc_finish is called later).  If tpc_abort is called later, changes
        must not persist.

        This includes conflict detection and handling.  If no conflicts or
        errors occur, the data manager should be prepared to make the
        changes persist when tpc_finish is called.
        """
        LOG.info("TRANSACTION: commit %s", self)

    def tpc_vote(self, transaction):
        """Verify that a data manager can commit the transaction.

        This is the last chance for a data manager to vote 'no'.  A
        data manager votes 'no' by raising an exception.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """
        LOG.info("TRANSACTION: tpc_vote %s", self)
        # TODO: last chance checks to see whether we sholud commit or not

    def tpc_finish(self, transaction):
        """Indicate confirmation that the transaction is done.

        Make all changes to objects modified by this transaction persist.

        transaction is the ITransaction instance associated with the
        transaction being committed.

        This should never fail.  If this raises an exception, the
        database is not expected to maintain consistency; it's a
        serious error.
        """
        LOG.info("TRANSACTION: tpc_finish %s", self)
        # ok let's work it out here:
        for identifier, graph in self.cache.items():
            LOG.info("                        put: %s", identifier)
            self.handler._do_put(graph)
        for identifier in self.to_remove:
            LOG.info("                        del: %s", identifier)
            self.handler._do_remove(identifier)
        self._reset()

    def tpc_abort(self, transaction):
        """Abort a transaction.

        This is called by a transaction manager to end a two-phase commit on
        the data manager.  Abandon all changes to objects modified by this
        transaction.

        transaction is the ITransaction instance associated with the
        transaction being committed.

        This should never fail.
        """
        LOG.info("TRANSACTION: tpc_abort %s", self)        
        self._reset()
        # TODO: undo changes, make sure nothing get's written to store

    def sortKey(self):
        """Return a key to use for ordering registered DataManagers.

        ZODB uses a global sort order to prevent deadlock when it commits
        transactions involving multiple resource managers.  The resource
        manager must define a sortKey() method that provides a global ordering
        for resource managers.
        """
        # Alternate version:
        #"""Return a consistent sort key for this connection.
        #
        #This allows ordering multiple connections that use the same storage in
        #a consistent manner. This is unique for the lifetime of a connection,
        #which is good enough to avoid ZEO deadlocks.
        #"""
        return 'rdfdm' + str(id(self))

    def savepoint(self):
        """Return a data-manager savepoint (IDataManagerSavepoint).

        this is called by a transaction in in case a saveponit is requested.
        """
        LOG.info("TRANSACTION: savepoint %s", self)        
        # TODO: return at least a Non RollBack Savepoint here.


class RDFSavePoint(object):

    implements(IDataManagerSavepoint)

    def rollback(self):
        """Rollback any work done since the savepoint.
        """
        pass


# class ISynchronizer(zope.interface.Interface):
#     """Objects that participate in the transaction-boundary notification API.
#     """

#     def beforeCompletion(transaction):
#         """Hook that is called by the transaction at the start of a commit.
#         """

#     def afterCompletion(transaction):
#         """Hook that is called by the transaction after completing a commit.
#         """

#     def newTransaction(transaction):
#         """Hook that is called at the start of a transaction.

#         This hook is called when, and only when, a transaction manager's
#         begin() method is called explictly.
#         """
