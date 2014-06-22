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
    # FIXME: this handler may have side effects.
    #    only the first .get call returns a new copy from the store.
    #    subsequent calls within transaction, return the same copp.
    #    => only one put is necessary at some time to persist all changes.
    #    Other handlers may not behave like that. (check wthere rdflib/zodb store get's a new graph each time? if yes I'll have to put after all cheanges done to local copy so that next get will get my changes)

    _dm = None

    def __init__(self, **kw):
        super(TransactionAwareHandler, self).__init__(**kw)
        LOG.info("Creating new handler")
        # FIXME create self._dm first, so that it is shared across threads. (it's a thread.local anyway)
        self._dm = ORDFDataManager(self)

    @property
    def dm(self):
        if not self._dm:
            self._dm = ORDFDataManager(self)
        return self._dm

    def get(self, identifier):
        identifier = get_identifier(identifier)
        result = self.dm.get(identifier)
        if result is None:
            result = super(TransactionAwareHandler, self).get(identifier)
            # dm.put(identifier, result) no need to cache/store a read only graph
            #   we only put stuff, that will be put back to store
            self.dm.put(result, False)
            # LOG.info("Handler: Return new graph %s", identifier)
        else:
            # LOG.info("Handler: Returned cached graph %s", identifier)
            pass
        return result

    def put(self, graph):
        if isinstance(graph, Graph):
            contexts = [graph]
        else:
            contexts = graph.contexts()
        for ctx in contexts:
            #identifier = get_identifier(ctx)
            self.dm.put(ctx)
        #LOG.info("Handler: schedule put(%s)", identifier)

    def append(self, frag):
        graph = self.get(frag.identifier)
        if graph is not None:
            graph += frag
        else:
            graph = frag
        self.put(graph)
        #LOG.info("Handler: schedule append(%s, %s)", frag.identifier)

    def remove(self, identifier):
        self.dm.remove(identifier)
        #LOG.info("Handler: schedule remove(%s)", identifier)

    def _do_put(self, graph):
        super(TransactionAwareHandler, self).put(graph)

    def _do_remove(self, identifier):
        super(TransactionAwareHandler, self).remove(identifier)


class ORDFDataManager(threading.local):
    # TODO: needs to change together with IORDF utility to make it thread safe.
    #       sometimes the wrong thread get's a wrong handler with a wrong dm.

    implements(ISavepointDataManager)

    transaction_manager = None

    handler = None

    def __init__(self, handler, tm=transaction.manager):
        self.handler = handler
        self.transaction_manager = tm
        self.transaction = None
        self.cache = {}
        self.to_remove = []
        self.modified = set()

    def _reset(self):
        self.cache = {}
        self.to_remove = []
        self.modified = set()
        #LOG.info("Clear for Handler")
        # everything finished now, we can safely unjoin the transaction
        # TODO: maybe check transaction state?
        # TODO: remove myself from Handler?
        self.transaction._unjoin(self)
        self.transaction = None

    def _join(self):
        if self.transaction is None:
            self.transaction = self.transaction_manager.get()
            #LOG.info("Join Transaction")
            self.transaction.join(self)

    def get(self, identifier):
        return self.cache.get(identifier, None)

    def put(self, graph, modified=True):
        '''
        assumes that a graph has been modified, unless overriden
        '''
        self._join()
        if modified:
            # if graph.identifier not in self.modified:
            #     LOG.info("MARK modified %s", graph.identifier)
            # else:
            #     LOG.info("Already marked modified %s", graph.identifier)
            self.modified.add(graph.identifier)
        # LOG.info("PUT graph %s into cache %s", graph.identifier, graph.identifier.__class__)
        self.cache[graph.identifier] = graph

    def remove(self, identifier):
        self._join()
        self.to_remove.append(identifier)

    def abort(self, transaction):
        #LOG.info("TRANSACTION: abort %s", self)
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
        #LOG.info("TRANSACTION: tpc_begin %s", self)
        # TODO: prepare whatever is necessary to commit transaction
        if self.transaction != transaction:
            LOG.fatal("Not My Transaction begin")
        pass

    def commit(self, transaction):
        """Commit modifications to registered objects.

        Save changes to be made persistent if the transaction commits (if
        tpc_finish is called later).  If tpc_abort is called later, changes
        must not persist.

        This includes conflict detection and handling.  If no conflicts or
        errors occur, the data manager should be prepared to make the
        changes persist when tpc_finish is called.
        """
        if self.transaction != transaction:
            LOG.fatal("Not My Transaction commit")
        #LOG.info("TRANSACTION: commit %s", self)
        # do changesets here
        if self.modified or self.to_remove:
            # FIXME: get real username and possibly create Agent here
            uname = 'Anonymous'
            reason = 'edited via web interface'
            cc = self.handler.context(user=uname, reason=reason)
            for identifier in self.modified:
                if identifier not in self.cache:
                    LOG.warn("modified identifier not found in cache: %s", identifier)
                    continue
                cc.add(self.cache[identifier])
                #remove changed graph from cache to force refetch for changeset
                del self.cache[identifier]
            # TODO: ideally we would generate a changeset to remove a graph
            #       but not sure how this would work, as the changeset removes
            #       only the triples for a graph, not the entire graph itself?
            #
            # this should add the changset graphs to the cache?
            cc.commit()
            # FIXEM: sometimes it happens that self.cache is empty aftec cc.commit, which should put all changed graphs back into cache via handler

    def tpc_vote(self, transaction):
        """Verify that a data manager can commit the transaction.

        This is the last chance for a data manager to vote 'no'.  A
        data manager votes 'no' by raising an exception.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """
        #LOG.info("TRANSACTION: tpc_vote %s", self)
        # TODO: last chance checks to see whether we sholud commit or not
        pass

    def tpc_finish(self, transaction):
        """Indicate confirmation that the transaction is done.

        Make all changes to objects modified by this transaction persist.

        transaction is the ITransaction instance associated with the
        transaction being committed.

        This should never fail.  If this raises an exception, the
        database is not expected to maintain consistency; it's a
        serious error.
        """
        if self.transaction != transaction:
            LOG.fatal("Not My Transaction finish")
        #LOG.info("TRANSACTION: tpc_finish %s", self)
        # ok let's work it out here:
        for identifier in self.modified:
            #for identifier, graph in self.cache.items():
            # LOG.info('Do Put for %s, (%s)', identifier, identifier.__class__)
            try:
                graph = self.cache[identifier]
                #LOG.info("                        put: %s", identifier)
                self.handler._do_put(graph)
            except KeyError:
                # TODO: This KeyError should never happen but if it does,
                #       we make sure not to kill the 2stage-commit.
                LOG.fatal("Modified graph %s not in cache during tpc_finish", identifier)

        for identifier in self.to_remove:
            #LOG.info("                        del: %s", identifier)
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
        if self.transaction != transaction:
            LOG.fatal("Not My Transaction abort")
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
        # TODO: return at least a Non RollBack Savepoint here.
        return RDFSavePoint(self)


class RDFSavePoint(object):

    implements(IDataManagerSavepoint)

    def __init__(self,  datamanager):
        LOG.info("SAVEPOINT: savepoint %s", self)
        self.dm = datamanager
        self.modified = self.dm.modified.copy()

    def rollback(self):
        """Rollback any work done since the savepoint.
        """
        LOG.info("SAVEPOINT: rollback %s", self)
        self.dm.modified = self.modified


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
