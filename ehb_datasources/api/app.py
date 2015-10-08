from collections import OrderedDict

from flask import Flask
from flask_restful import Resource, Api, fields, marshal_with, marshal

from ehb_datasources.drivers import nautilus, phenotype, redcap
from ehb_datasources import get_version
from ehb_datasources.api.resources.redcap import Redcap

app = Flask(__name__)
api = Api(app)


class Driver(object):
    '''
    This object handles the representation of a Driver in the initial API index.
    '''
    def __init__(self, name):
	self.name = name


api.add_resource(Redcap, '/redcap', '/redcap/<form_type>', endpoint='redcap')

# Define driver's to be listed in initial index
redcap_driver = Driver(name='Redcap')
redcap_fields = {
    'name': fields.String,
    'uri': fields.Url('redcap', absolute=True)
}


class Index(Resource):
    '''
    The index resources provides version info and available drivers at the root
    endpoint.
    '''
    def get(self):
	ix = OrderedDict()
	ix['name'] = 'ehb_datasources'
	ix['drivers'] = [
	    marshal(redcap_driver, redcap_fields),
	]
	ix['version'] = get_version()
	return ix

api.add_resource(Index, '/')

if __name__ == '__main__':
    app.run(debug=True)
