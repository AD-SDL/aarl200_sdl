from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.types.action_types import ActionRequest
from madsci.common.types.location_types import LocationArgument

client = RestNodeClient(url="http://controlroom1.cse.anl.gov:3011/")
client.send_admin_command("reset")