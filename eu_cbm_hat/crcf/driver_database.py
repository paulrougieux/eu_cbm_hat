import pandas

from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


class Base(DeclarativeBase):
    pass

class Status(Base):
    __tablename__ = 'status'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    species = relationship("Species", back_populates="status")

class ForestType(Base):
    __tablename__ = 'forest_type'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    species = relationship("Species", back_populates="forest_type")

class Region(Base):
    __tablename__ = 'region'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    species = relationship("Species", back_populates="region")

class ManagementType(Base):
    __tablename__ = 'mgmt_type'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    species = relationship("Species", back_populates="mgmt_type")

class ManagementStrategy(Base):
    __tablename__ = 'mgmt_strategy'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    species = relationship("Species", back_populates="mgmt_strategy")

class Climate(Base):
    __tablename__ = 'climate'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    species = relationship("Species", back_populates="climate")

class ConBroad(Base):
    __tablename__ = 'con_broad'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    species = relationship("Species", back_populates="con_broad")

class SiteIndex(Base):
    __tablename__ = 'site_index'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    species = relationship("Species", back_populates="site_index")

class GrowthPeriod(Base):
    __tablename__ = 'growth_period'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))

class Disturbance(Base):
    __tablename__ = 'disturbance'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True)
    description = Column(String(100))
    simulations = relationship("Simulation", back_populates="disturbance")



class Species(Base):

    __tablename__ = 'species'

    id = Column(Integer, primary_key=True, autoincrement=True)
    status_id = Column(Integer, ForeignKey('status.id'))
    forest_type_id = Column(Integer, ForeignKey('forest_type.id'))
    region_id = Column(Integer, ForeignKey('region.id'))
    mgmt_type_id = Column(Integer, ForeignKey('mgmt_type.id'))
    mgmt_strategy_id = Column(Integer, ForeignKey('mgmt_strategy.id'))
    climate_id = Column(Integer, ForeignKey('climate.id'))
    con_broad_id = Column(Integer, ForeignKey('con_broad.id'))
    site_index_id = Column(Integer, ForeignKey('site_index.id'))

    status = relationship("Status", back_populates="species")
    forest_type = relationship("ForestType", back_populates="species")
    region = relationship("Region", back_populates="species")
    mgmt_type = relationship("ManagementType", back_populates="species")
    mgmt_strategy = relationship("ManagementStrategy", back_populates="species")
    climate = relationship("Climate", back_populates="species")
    con_broad = relationship("ConBroad", back_populates="species")
    site_index = relationship("SiteIndex", back_populates="species")
    simulations = relationship("Simulation", back_populates="species")


class Simulation(Base):

    __tablename__ = 'simulation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    species_id = Column(Integer, ForeignKey('species.id'))
    disturbance_id = Column(Integer, ForeignKey('disturbance.id'))
    start = Column(Integer)
    index = Column(Integer)

    species = relationship("Species", back_populates="simulations")
    disturbance = relationship("Disturbance", back_populates="simulations")



class Database:

    def __init__(self, path:str):

        # create engine
        self.engine = create_engine(path)

        # enable foreign key constraints for SQLite
        if path.startswith('sqlite'):
            self._enable_sqlite_foreign_keys()

        # create session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()


    def _enable_sqlite_foreign_keys(self):

        from sqlalchemy import event
        @event.listens_for(self.engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


    def init(self,
             classifiers:dict[str,dict[str,str]],
             disturbances:dict[str,str],
            ):

        # create db
        Base.metadata.create_all(self.engine)

        # populate classifiers table
        models = {'status': Status,
                  'forest_type': ForestType,
                  'region': Region,
                  'mgmt_type': ManagementType,
                  'mgmt_strategy': ManagementStrategy,
                  'climate': Climate,
                  'con_broad': ConBroad,
                  'site_index': SiteIndex,
                  'growth_period': GrowthPeriod,
                 }
        records = []
        self.classif_ids = {}
        for key, values in classifiers.items():
            if key not in models:
                continue
            record = models[key]
            self.classif_ids[key] = {}
            for idx, (code, description) in enumerate(values.items()):
                records.append(record(code=code, description=description))
                self.classif_ids[key][code] = idx+1

        # populate disturbances table
        self.disturbance_ids = {}
        for idx, (code, description) in enumerate(disturbances.items()):
            records.append(Disturbance(code=code, description=description))
            self.disturbance_ids[code] = idx+1

        # commit
        self.session.add_all(records) 
        self.session.commit()


    def classifier_ids(self, table:str)->dict[str,str]:
        return {key:str(value) for key, value in self.classif_ids[table].items()}


    def add_commit_species(self, species:dict)->int:
        record = Species(
            status_id        = self.classif_ids['status'][species['status']],
            forest_type_id   = self.classif_ids['forest_type'][species['forest_type']],
            region_id        = self.classif_ids['region'][species['region']],
            mgmt_type_id     = self.classif_ids['mgmt_type'][species['mgmt_type']],
            mgmt_strategy_id = self.classif_ids['mgmt_strategy'][species['mgmt_strategy']],
            climate_id       = self.classif_ids['climate'][str(species['climate'])],
            con_broad_id     = self.classif_ids['con_broad'][species['con_broad']],
            site_index_id    = self.classif_ids['site_index'][str(species['site_index'])],
        )
        self.session.add(record)
        self.session.commit()
        return record.id


    def add_simulation(self, species_id:int, disturbance_code:int, start:int, index:int):
        record = Simulation(
            species_id     = species_id,
            disturbance_id = self.disturbance_ids[disturbance_code],
            start          = start,
            index          = index,
        )
        self.session.add(record)
        self.session.commit()


    def commit(self):
        self.session.commit()


    def get_simulations(self,
                        status=None,
                        forest_type=None,
                        region=None,
                        mgmt_type=None,
                        mgmt_strategy=None,
                        climate=None,
                        con_broad=None,
                        site_index=None,
                        disturbance=None)->pandas.DataFrame:

        query = self.session.query(Simulation).join(Simulation.species)
        if disturbance:
            query = query.join(Simulation.disturbance).filter(Disturbance.code == disturbance)
        if status:
            query = query.join(Species.status).filter(Status.code == status)
        if forest_type:
            query = query.join(Species.forest_type).filter(ForestType.code == forest_type)
        if region:
            query = query.join(Species.region).filter(Region.code == region)
        if mgmt_type:
            query = query.join(Species.mgmt_type).filter(ManagementType.code == mgmt_type)
        if mgmt_strategy:
            query = query.join(Species.mgmt_strategy).filter(ManagementStrategy.code == mgmt_strategy)
        if climate:
            query = query.join(Species.climate).filter(Climate.code == climate)
        if con_broad:
            query = query.join(Species.con_broad).filter(ConBroad.code == con_broad)
        if site_index:
            query = query.join(Species.site_index).filter(SiteIndex.code == site_index)
        sims = query.all()

        sims = [(sim.species.status.code,
                 sim.species.forest_type.code,
                 sim.species.region.code,
                 sim.species.mgmt_type.code,
                 sim.species.mgmt_strategy.code,
                 sim.species.climate.code,
                 sim.species.con_broad.code,
                 sim.species.site_index.code,
                 sim.disturbance.code,
                 sim.start,
                 sim.index) for sim in sims]

        df = pandas.DataFrame(sims, columns=['status', 'forest_type', 'region', 'mgmt_type', 'mgmt_strategy', 'climate', 'con_broad', 'site_index', 'disturbance', 'start', 'index'])
        return df


    def get_classifiers(self, table_name:str)->pandas.DataFrame:

        match table_name:
            case 'status':
                records = self.session.query(Status).all()
            case 'forest_type':
                records = self.session.query(ForestType).all()
            case 'region':
                records = self.session.query(Region).all()
            case 'mgmt_type':
                records = self.session.query(ManagementType).all()
            case 'mgmt_strategy':
                records = self.session.query(ManagementStrategy).all()
            case 'climate':
                records = self.session.query(Climate).all()
            case 'con_broad':
                records = self.session.query(ConBroad).all()
            case 'site_index':
                records = self.session.query(SiteIndex).all()
            case 'growth_period':
                records = self.session.query(GrowthPeriod).all()
            case 'disturbance':
                records = self.session.query(Disturbance).all()
            case _:
                raise ValueError(f"Unknown table: {table_name}")

        codes = [(record.code, record.description) for record in records]
        return pandas.DataFrame(codes, columns=['code', 'description'])


    def close(self):
        self.session.close()