import config
import defaults
import os
import sys
import pathlib
from pathlib import Path
from pprint import pprint
import argparse
import logging
from jinja2 import Template

def setup_logging():
	parser = argparse.ArgumentParser()
	parser.add_argument(
	    '-d', '--debug',
	    help="Print lots of debugging statements",
	    action="store_const", dest="loglevel", const=logging.DEBUG,
	    default=logging.WARNING,
	)
	parser.add_argument(
	    '-v', '--verbose',
	    help="Be verbose",
	    action="store_const", dest="loglevel", const=logging.INFO,
	)
	args = parser.parse_args()    
	logging.basicConfig(level=args.loglevel)


class Node:
	def __init__(self, node_body):
		self.body = node_body
		lines = node_body.splitlines()
		name = ""
		self.parameters = {}
		last_name = ""
		for line in lines:
			if line == "  }":
				name = ""
			elif line.endswith("{"):
				name = line[0:-1].strip()
				last_name = name
			elif line == "}":
				pass
			else:
				parts = line.split(":")
				if name == "":
					if len(parts) == 1:
						self.parameters["text"] = self.parameters["text"] + parts[0]
					else:
						self.parameters[parts[0].strip()] = parts[1].strip()
				else:
					self.parameters[F"{name}.{parts[0].strip()}"] = parts[1].strip()
		self.id = self.parameters["id"]
		if "parent" in self.parameters:
			self.parent = self.parameters["parent"]
		else:
			self.parent = False
		self.childs = []

class Generator:
	def need_to_write(self, output_file):
		if (os.path.isdir(output_file)):
			logging.error(F"{output_file} is dir")
			return False
		if not os.path.isfile(output_file):
			return True
		if config.GENERATED_FLAG in open(output_file, 'r').read():
			return True
		return False

	def parse_nodes(self):
		self.nodes = {}
		lines = self.gui_body.splitlines()
		node_body = ""
		to_add = False
		self.script = False
		for line in lines:
			l = line.rstrip()
			if l.startswith("script:"):
				self.script = l.split('"')[1]
			if l == "nodes {":
				node_body = ""
				to_add = True
			if l == "}" and to_add:
				node_body = F"{node_body}{l}\n"
				node = Node(node_body)
				self.nodes[node.id] = node
				to_add = False
			if to_add:
				node_body = F"{node_body}{l}\n"

	def make_structure_field(self):
		self.structure = ""
		for node in self.short_list:
			typ = node.parameters["type"]
			if typ == "TYPE_TEMPLATE":
				self.structure = F"{self.structure}{'  ' * node.deep}{node.id[1:-1]} ({typ}) {node.parameters['template'][1:-1]}\n"
			else:
				self.structure = F"{self.structure}{'  ' * node.deep}{node.id[1:-1]} ({typ})\n"

	def req_structure(self, node):
		self.list.append(node)
		for child in node.childs:
			self.req_structure(self.nodes[child])

	def req_short_structure(self, node):
		self.short_list.append(node)
		if node.parameters["template_node_child"] == "false" and node.parameters["type"] == "TYPE_TEMPLATE":
			self.templates.add(config.DRUID_PATH + node.parameters['template'][2:-1])
			return
		for child in node.childs:
			self.req_short_structure(self.nodes[child])

	def make_list(self):
		self.list = []
		for i in self.nodes:
			node = self.nodes[i]
			if not node.parent:
				self.req_structure(node)

	def make_short_list(self):
		self.short_list = []
		self.templates = set()
		for i in self.nodes:
			node = self.nodes[i]
			if not node.parent:
				self.req_short_structure(node)

	def create_structure(self):
		for i in self.nodes:
			node = self.nodes[i]
			if node.parent:
				self.nodes[node.parent].childs.append(node.id)


	def get_deep(self, node):
		if node.parent:
			return self.get_deep(self.nodes[node.parent]) + 1
		else:
			return 0

	def calc_deep(self):
		for i in self.nodes:
			node = self.nodes[i]
			node.deep = self.get_deep(node)

	def human_name(self, ID):
		parts = ID.split('_')
		result = ""
		for part in parts:
			result = F"{result} {result.capitalize()}"
		return result.split()

	def node_diff(self, node, template):
		result = {}
		for i in node.parameters:
			value = node.parameters[i]
			if (i not in template.parameters) or (value != template.parameters[i]):
				result[i] = value
		return result

	def find_diff(self):
		self.elements = {}
		for i in self.nodes:
			node = self.nodes[i]
			ID = node.id[1:-1]
			if (node.parameters["type"] == "TYPE_BOX"):
				self.elements[ID] = self.node_diff(node, self.default_node_box)
			if (node.parameters["type"] == "TYPE_TEXT"):
				self.elements[ID] = self.node_diff(node, self.default_node_text)

	def load_body(self):
		if self.script:
			self.gui_script_body = open(F"druid{self.script}", 'r').read()
		else:
			self.gui_script_body = False

	def gen_child_templates(self):
		self.child_templates = {}
		for t in self.templates:
			self.child_templates[t] = Generator()
			self.child_templates[t].gen_file(t)
			print(t)
			print(self.child_templates[t].structure)
		r = {}
		for t in self.child_templates:
			for t2 in self.child_templates[t].child_templates:
				r[t2] = self.child_templates[t].child_templates[t2]
		for t in r:
			self.child_templates[t] = r[t]


	def gen_file(self, gui_path):
		self.gui_path = gui_path
		self.gui_body = open(gui_path, 'r').read()
		#self.gui_script_body = open(gui_script_path, 'r').read()
		self.parse_nodes()
		self.create_structure()
		self.calc_deep()
		self.make_list()
		self.make_short_list()
		self.make_structure_field()
		self.find_diff()
		self.load_body()
		self.gen_child_templates()

	def generate(self):
		logging.debug(F"EXAMPLES_PATH: {config.EXAMPLES_PATH}")
		logging.debug(F"OUTPUT_PATH: {config.OUTPUT_PATH}")
		template_body = open('template.jinja', 'r').read()
		self.template = Template(template_body, keep_trailing_newline=True)
		for self.group in os.listdir(config.EXAMPLES_PATH[1:]):
			if 'template' == self.group:
				continue
			output_path = F"{config.OUTPUT_PATH}/{self.group}"
			group_path = F"{config.EXAMPLES_PATH}/{self.group}"
			for self.example in os.listdir(group_path[1:]):
				gui_path = F"{config.EXAMPLES_PATH}/{self.group}/{self.example}/{self.example}.gui"
				gui_path = gui_path[1:]
				if not os.path.isfile(gui_path):
					logging.error(F"File not found: {gui_path}")
					continue
				Path(F"{config.OUTPUT_PATH}/{self.group}").mkdir(exist_ok=True)
				output_file = F"{output_path}/{self.example}.md"
				logging.debug("== Generate file ==")
				logging.debug(F"output_file: {output_file}")
				logging.debug(F"gui_path: {gui_path}")
				#logging.debug(F"gui_script_path: {gui_script_path}")
				if not self.need_to_write(output_file):
					logging.info(F"Skip: {output_file}")
					continue
				self.gen_file(gui_path)
				open(output_file, 'w').write(self.template.render(d = self))

	def __init__(self):
		self.default_node_box = Node(defaults.DEFAULT_BOX)
		self.default_node_text = Node(defaults.DEFAULT_TEXT)


if __name__ == '__main__':
	setup_logging()
	generator = Generator()
	generator.generate()
