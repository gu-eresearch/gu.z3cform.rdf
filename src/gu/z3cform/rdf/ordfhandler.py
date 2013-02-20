import transaction
import logging
from transaction.interfaces import ISavepointDataManager, IDataManagerSavepoint
from zope.interface import implements
from ordf.handler import Handler
# transaction aware ordf handler

# /Users/gerhard/Downloads/buildout/eggs/alm.solrindex-1.1.1-py2.7.egg/alm/solrindex/index.py
# /Users/gerhard/Downloads/buildout/eggs/collective.indexing-2.0a3-py2.7.egg/collective/indexing/transactions.py
# /Users/gerhard/Downloads/buildout/eggs/p01.fsfile-0.6.0-py2.7.egg/p01/fsfile/storage.py
# /Users/gerhard/Downloads/buildout/eggs/p01.fsfile-0.6.0-py2.7.egg/p01/fsfile/tm.py
# /Users/gerhard/Downloads/buildout/eggs/p01.tmp-0.6.0-py2.7.egg/p01/tmp/file.py
# /Users/gerhard/Downloads/buildout/eggs/z3c.indexer-0.6.0-py2.7.egg/z3c/indexer/interfaces.py
# /Users/gerhard/Downloads/buildout/eggs/zope.sendmail-3.7.5-py2.7.egg/zope/sendmail/delivery.py

LOG = logging.getLogger(__name__)

class TransactionAwareHandler(Handler):

    def put(self, *av, **kw):
        tn = transaction.get()
        LOG.info("Handler: schedule put(%s, %s)", repr(av), repr(kw))
        dh = ORDFDataManager(super(TransactionAwareHandler, self).put, *av, **kw)
        tn.join(dh)

    def append(self, *av, **kw):
        tn = transaction.get()
        LOG.info("Handler: schedule append(%s, %s)", repr(av), repr(kw))
        dh = ORDFDataManager(super(TransactionAwareHandler, self).append, *av, **kw)
        tn.join(dh)
        
    def remove(self, *av, **kw):
        tn = transaction.get()
        LOG.info("Handler: schedule remove(%s, %s)", repr(av), repr(kw))
        dh = ORDFDataManager(super(TransactionAwareHandler, self).remove, *av, **kw)
        tn.join(dh)



class ORDFDataManager(object):

    implements(ISavepointDataManager)

    transaction_manager = transaction.manager

    def __init__(self, func, *args, **kw):
        self.func = func
        self.args = args
        self.kw = kw

    def funcrepr(self):
        return "%s.%s(%s)" % (self.func.im_class.__name__, self.func.__name__, ', '.join((', '.join((str(a) for a in self.args)), ', '.join('%s=%s' % (strt(k), str(v)) for (k, w) in self.kw.items()))))

    def abort(self, transaction):
        LOG.info("TRANSACTION: abort %s", self.funcrepr())
    
    # Two-phase commit protocol.  These methods are called by the ITransaction
    # object associated with the transaction being committed.  The sequence
    # of calls normally follows this regular expression:
    #     tpc_begin commit tpc_vote (tpc_finish | tpc_abort)

    def tpc_begin(self, transaction):
        """Begin commit of a transaction, starting the two-phase commit.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """
        LOG.info("TRANSACTION: tpc_begin %s", self.funcrepr())
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
        LOG.info("TRANSACTION: commit %s", self.funcrepr())
        # TODO: apply changes to underlying object (not store), make sure transaction will commit

    def tpc_vote(self, transaction):
        """Verify that a data manager can commit the transaction.

        This is the last chance for a data manager to vote 'no'.  A
        data manager votes 'no' by raising an exception.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """
        LOG.info("TRANSACTION: tpc_vote %s", self.funcrepr())
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
        LOG.info("TRANSACTION: tpc_finish %s", self.funcrepr())
        # ok let's work it out here:
        self.func(*self.args, **self.kw)

    def tpc_abort(self, transaction):
        """Abort a transaction.

        This is called by a transaction manager to end a two-phase commit on
        the data manager.  Abandon all changes to objects modified by this
        transaction.

        transaction is the ITransaction instance associated with the
        transaction being committed.

        This should never fail.
        """
        LOG.info("TRANSACTION: tpc_abort %s", self.funcrepr())        
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
        LOG.info("TRANSACTION: savepoint %s", self.funcrepr())        
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
