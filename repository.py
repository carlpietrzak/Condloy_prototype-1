import abc
import model

class AbstractRepository(abc.ABC):

    @abc.abstractmethod
    def add_task(self, task):
        raise NotImplementedError

    @abc.abstractmethod
    def get_task(self, id):
        raise NotImplementedError

    @abc.abstractmethod
    def get_proposal(self, id):
        raise NotImplementedError




class SqlAlchemyRepository(AbstractRepository):

    def __init__(self, session):
        self.session = session

    def add_task(self, task):
        self.session.add(task)

    def get_task(self, id):
        return self.session.query(model.Task).filter_by(id=id).one()

    def get_proposal(self, id):
        return self.session.query(model.Proposal).filter_by(id=id).one()

    def get_all_tasks(self):
        return self.session.query(model.Task).all()

    def get_all_proposals(self):
        return self.session.query(model.Proposal).all()

