from oslo.config import cfg
import random, traceback
from oscard import log
from oscard.sim.proxy import ProxyAPI

sim_group = cfg.OptGroup(name='sim')
sim_opts = [
	cfg.IntOpt(
		name='no_t',
		default=10,
		help='The number of steps of the simulation'
	),
	cfg.ListOpt(
		name='proxy_hosts',
		default=['0.0.0.0:3000', ],
		help='Oscard proxy host'
	)
]

CONF = cfg.CONF
CONF.register_group(sim_group)
CONF.register_opts(sim_opts, sim_group)
LOG = log.get_logger(__name__)

proxies = [ProxyAPI(host) for host in CONF.sim.proxy_hosts]

# Virtual classes for commands
class BaseCommand(object):
	'''
		The abstract command interface
	'''
	name = 'base_command'

	def execute(self, proxy, ctxt):
		# invoke nova apis
		# use context
		# return new context
		return {}

	class Meta:
		abstract = True

class CreateCommand(BaseCommand):
	name = 'create'

	def execute(self, proxy, ctxt):
		try:
			resp = proxy.create()
			ctxt.append(resp['id'])

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(traceback.format_exc())
		finally:
			return ctxt

class DestroyCommand(BaseCommand):
	name = 'destroy'

	def execute(self, proxy, ctxt):
		try:
			resp = proxy.destroy()
			ctxt.remove(resp['id'])

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(traceback.format_exc())
		finally:
			return ctxt

class ResizeCommand(BaseCommand):
	name = 'resize'

	def execute(self, proxy, ctxt):
		try:
			resp = proxy.resize()

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(traceback.format_exc())
		finally:
			return ctxt

def main():
	from oscard import config, log
	config.init_conf()
	
	LOG = log.get_logger(__name__)

	cmds = [
		CreateCommand,
		ResizeCommand,
		DestroyCommand,
	]

	ctxts = {}
	for p in proxies:
		ctxts[p.host] = []

	for p in proxies:
		for t in xrange(CONF.sim.no_t):
			if len(ctxts[p.host]) > 0:
				cmd = random.choice(cmds)()
			else: #there are no virtual machines... let's spawn one!
				cmd = CreateCommand()
				
			LOG.info(p.host + ': ' + str(t) + ' --> ' + cmd.name)
			
			ctxts[p.host] = cmd.execute(p, ctxts[p.host])

		LOG.info(p.host + ': simulation ENDED')

		# TODO remove these lines
		import time
		LOG.info(p.host + ': destroying all remaining instances in 60 seconds')
		for t in xrange(1, 61):
			if t % 5 == 0:
				LOG.info(str(60 - t) + ' seconds to destroy...')
			time.sleep(1)

		for id in ctxts[p.host]:
			p.destroy(id=id)