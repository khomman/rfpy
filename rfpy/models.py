from rfpy import db


class Stations(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station = db.Column(db.String(10), index=True, unique=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    elevation = db.Column(db.Float)
    status = db.Column(db.String(1))

    # Set the relationship to the rftn table with a backref.  That way we can
    # get the station details from the receiver functions table
    receiver_functions = db.relationship('ReceiverFunctions',
                                         backref='station_receiver_functions',
                                         lazy='dynamic')
    data = db.relationship('RawData', backref='station_data', lazy='dynamic')
    hks = db.relationship('HKResults', backref='hk_station', lazy='dynamic')

    def __repr__(self):
        return f'<Station: {self.id}, {self.station}, {self.latitude}, '\
                f'{self.longitude}, {self.elevation}, {self.status}>'

    def as_dict(self):
        return {'ID': self.id, 'Station': self.station,
                'Latitude': self.latitude, 'Longitude': self.longitude,
                'Elevation': self.elevation, 'Status': self.status}


class Arrivals(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    arr_type = db.Column(db.String(2))
    time = db.Column(db.String(20))
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'))
    eq_id = db.Column(db.Integer, db.ForeignKey('earthquakes.id'))
    rayp = db.Column(db.Float)
    inc_angle = db.Column(db.Float)
    take_angle = db.Column(db.Float)

    earthquake = db.relationship('Earthquakes', backref='earthquake_arr')
    station = db.relationship('Stations', backref='station_arr')

    def as_dict(self):
        return {'ID': self.id, 'Type': self.arr_type,
                'Arrival Time': self.time, 'Station': self.station.station,
                'Earthquake': self.eq_id}

    def __repr__(self):
        return f'<Arrival: Type {self.arr_type}, Station {self.station_id}'\
               f'Earthquake {self.eq_id}>'


class Earthquakes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.String(99), unique=True)
    origin_time = db.Column(db.String(15))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    depth = db.Column(db.Float)
    utilized = db.Column(db.Boolean)

    def as_dict(self):
        return {'ID': self.id, 'Time': self.origin_time,
                'Latitude': self.latitude, 'Longitude': self.longitude,
                'Depth': round(self.depth/1000, 2), 'Used': self.utilized}

    def __repr__(self):
        return f'<EQ: {self.id}, Lat: {self.latitude}, Lon: {self.longitude}'\
                f'Depth (m): {self.depth}>'


class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'))
    filt_id = db.Column(db.Integer, db.ForeignKey('filters.id'))
    status = db.Column(db.String(2))

    station = db.relationship('Stations', backref='station_status',
                              uselist=False)
    filt = db.relationship('Filters', backref='filter_status',
                           uselist=False)

    def __repr__(self):
        return f'<Status {self.id}: {self.status}>'


class RawData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sta_id = db.Column(db.Integer, db.ForeignKey('stations.id'))
    earthquake_id = db.Column(db.Integer, db.ForeignKey('earthquakes.id'))
    path = db.Column(db.String(255), index=True, unique=True)
    new_data = db.Column(db.Boolean)

    station = db.relationship('Stations', backref='station_raw_data',
                              uselist=False)
    earthquake = db.relationship('Earthquakes', backref='earthquake_raw_data')

    def as_dict(self):
        return {'ID': self.id, 'Station': self.station.station,
                'Path': self.path, 'New': self.new_data}

    def __repr__(self):
        return f'<Data: {self.id}, Station: {self.station}>'


class Filters(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filter = db.Column(db.Float, unique=True)

    receiver_functions = db.relationship('ReceiverFunctions',
                                         backref='filter_receiver_functions',
                                         lazy='dynamic')
    hks = db.relationship('HKResults', backref='hk_filter', lazy='dynamic')

    def __repr__(self):
        return f'<Filter Center: {self.id}, {self.filter}'

    def as_dict(self):
        return {'ID': self.id, 'Filter': self.filter}


class HKResults(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station = db.Column(db.Integer, db.ForeignKey('stations.id'))
    filter = db.Column(db.Integer, db.ForeignKey('filters.id'))
    hkpath = db.Column(db.String(255))
    savedhkpath = db.Column(db.String(255))
    h = db.Column(db.Float)
    sigmah = db.Column(db.Float)
    k = db.Column(db.Float)
    sigmak = db.Column(db.Float)
    vp = db.Column(db.Float)

    def __repr__(self):
        return f'<Station: {self.station}, H: {self.h}, K: {self.k}>'

    def as_dict(self):
        return {'ID': self.id, 'Station': self.hk_station.station,
                'Filter': self.hk_filter.filter, 'Depth': self.h,
                'Sigmah': round(self.sigmah, 1), 'Kappa': self.k,
                'Sigmak': round(self.sigmak, 2), 'Vp': self.vp}


class ReceiverFunctions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station = db.Column(db.Integer, db.ForeignKey('stations.id'))
    filter = db.Column(db.Integer, db.ForeignKey('filters.id'))
    path = db.Column(db.String(255), index=True, unique=True)
    new_receiver_function = db.Column(db.Boolean)
    accepted = db.Column(db.Boolean)

    def __repr__(self):
        return f'<Station: {self.station} id: {self.id}, Accepted:'\
                f'{self.accepted}'

    def as_dict(self):
        return {'ID': self.id,
                'Station': self.station_receiver_functions.station,
                'Filter': self.filter_receiver_functions.filter,
                'Path': self.path, 'NewData': self.new_receiver_function,
                'Accepted': self.accepted}
