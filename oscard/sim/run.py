from oscard import config
config.init_conf()

from oslo.config import cfg
import random, traceback
from oscard import log
from oscard.sim.proxy import ProxyAPI
from oscard.sim.collector import BifrostAPI

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
bifrost = BifrostAPI()

# Virtual classes for commands
class BaseCommand(object):
	'''
		The abstract command interface
	'''
	name = 'base_command'

	def execute(self, proxy, count):
		# invoke nova apis
		# use context
		# return new context
		return {}

	class Meta:
		abstract = True

class CreateCommand(BaseCommand):
	name = 'create'

	def execute(self, proxy, count):
		try:
			resp = proxy.create()
			count += 1

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(traceback.format_exc())
		finally:
			return count

class DestroyCommand(BaseCommand):
	name = 'destroy'

	def execute(self, proxy, count):
		try:
			resp = proxy.destroy()
			count -= 1

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(traceback.format_exc())
		finally:
			return count

class ResizeCommand(BaseCommand):
	name = 'resize'

	def execute(self, proxy, count):
		try:
			resp = proxy.resize()

			LOG.info(str(resp))
		except Exception as e:
			LOG.error(traceback.format_exc())
		finally:
			return count

def main():
	no_steps = CONF.sim.no_t
	cmds = [
		CreateCommand,
		ResizeCommand,
		DestroyCommand,
	]

	counts = {}
	hosts_dict = {}
	for p in proxies:
		counts[p.host] = 0

		sim_type = 'smart' if p.is_smart()['smart'] else 'normal'
		hosts_dict[p.host] = sim_type

	bifrost.add_sim(no_steps, hosts_dict)

	for t in xrange(no_steps):
		cmd = {}
		for p in proxies:
			if counts[p.host] > 0:
				cmd[p.host] = random.choice(cmds)()
			else: #there are no virtual machines... let's spawn one!
				cmd[p.host] = CreateCommand()
			
			LOG.info(p.host + ': ' + str(t) + ' --> ' + cmd[p.host].name)
		
			counts[p.host] = cmd[p.host].execute(p, counts[p.host])

			snapshot = p.snapshot()
			bifrost.add_snapshot(p.host, t, cmd[p.host].name, snapshot)

	LOG.info(p.host + ': simulation ENDED')
	bifrost.add_end_to_current_sim()

	import time
	for p in proxies:
		# removing all remaining instances
		TIMEOUT = 30
		LOG.info(p.host + ': destroying all remaining instances in ' + str(TIMEOUT) + ' seconds')
		for t in xrange(1, TIMEOUT + 1):
			if t % 5 == 0:
				LOG.info(str(TIMEOUT - t) + ' seconds to destroy...')
			time.sleep(1)

		for times in xrange(counts[p.host]):
			resp = p.destroy()
			LOG.info(str(resp))