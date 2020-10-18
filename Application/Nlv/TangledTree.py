#
# Copyright (C) Niel Clausen 2020. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#

#
# Motivated by https://observablehq.com/@nitaku/tangled-tree-visualization-ii
#

import json



## Data ####################################################

class Data:

    #-------------------------------------------------------
    def __eq__(self, other):
        return self.Id == other.Id

    def __lt__(self, other):
        return self.Id < other.Id

    def __hash__(self):
        return hash(self.Id)

    def __repr__(self):
        return self.Name



## D_Entity ################################################

class D_Entity(Data):

    #-------------------------------------------------------
    def __init__(self, name, properties):
        self.Properties = properties
        self.Id = properties["event_id"]
        self.Name = name

        self.ParentEntities = []
        self.ChildEntities = []
        self.ParentBundle = None
        self.ChildBundles = []
        self.Level = None


    #-------------------------------------------------------
    def RecordParent(self, parent_entity):
        self.ParentEntities.append(parent_entity)


    #-------------------------------------------------------
    def RecordChild(self, child_entity):
        self.ChildEntities.append(child_entity)


    #-------------------------------------------------------
    def HasParents(self):
        return self.ParentEntities

    def IsConnected(self):
        return self.ParentEntities or self.ChildEntities

    def CreateBundles(self, network):
        if self.HasParents():
            bundle = self.ParentBundle = network.GetBundle(self.ParentEntities)
            bundle.AddChildEntity(self)

    def RecordChildBundle(self, bundle):
        self.ChildBundles.append(bundle)


    #-------------------------------------------------------
    def AssignNodeLevel(self):
        if self.ParentBundle is not None:
            self.Level = self.ParentBundle.Level + 1
        else:
            self.Level = min([bundle.Level for bundle in self.ChildBundles])



## D_Bundle ################################################

class D_Bundle(Data):
    "Graphical layout data for a group of Links - a bundle of vertical connections"

    #-------------------------------------------------------
    def __init__(self, id, name, parents):
        self.Generation = None
        self.Level = None
        self.Id = id
        self.Name = name
        self.ParentEntities = sorted(parents)
        self.ChildEntities = []
        self.ChildBundles = []


    #-------------------------------------------------------
    def AddChildEntity(self, child):
        self.ChildEntities.append(child)


    #-------------------------------------------------------
    def SetHierarchy(self):
        "Form a traversable hierarchy of bundles"
        parent_bundles = self.ParentBundles = set([parent.ParentBundle for parent in self.ParentEntities if parent.ParentBundle is not None])
        for bundle in parent_bundles:
            bundle.ChildBundles.append(self)

        for parent in self.ParentEntities:
            parent.RecordChildBundle(self)


    #-------------------------------------------------------
    def HasChildren(self):
        return len(self.ChildBundles) != 0

    def HasParents(self):
        return len(self.ParentBundles) != 0


    #-------------------------------------------------------
    def SetLevel(self, min_generation):
        self.Level = self.Generation - min_generation
    

    #-------------------------------------------------------
    def AssignAncestorGeneration(self, generation, discovered):
        if self.Generation is None or generation < self.Generation:
            self.Generation = generation
            discovered.add(self)
            self.AssignAncestorsGeneration(generation, discovered)


    def AssignAncestorsGeneration(self, generation, discovered):
        if generation is None:
            generation = self.Generation

        for parent in self.ParentBundles:
            parent.AssignAncestorGeneration(generation - 1, discovered)

        return discovered


    def AssignDescendentGeneration(self, generation, discovered):
        if self.Generation is None or generation > self.Generation:
            self.Generation = generation
            discovered.add(self)
            self.AssignDescendentsGeneration(generation, discovered)

    def AssignDescendentsGeneration(self, generation, discovered):
        if generation is None:
            generation = self.Generation

        for child in self.ChildBundles:
            child.AssignDescendentGeneration(generation + 1, discovered)

        return discovered


    def AssignGeneration(self, generation):
        self.Generation = generation
        ancestors = self.AssignAncestorsGeneration(generation, set())
        descendents = self.AssignDescendentsGeneration(generation, set())

        while len(ancestors) != 0 or len(descendents) != 0:
            next_ancestors = set()
            next_descendents = set()

            for ancestor in ancestors:
                ancestor.AssignDescendentsGeneration(None, next_descendents)

            for descendent in descendents:
                descendent.AssignAncestorsGeneration(None, next_ancestors)

            ancestors = next_ancestors
            descendents = next_descendents




## D_NetworkBuilder ########################################

class D_NetworkBuilder:

    #-------------------------------------------------------
    def __init__(self):
        self.Entities = dict()
        self.Links = dict()
        self.Bundles = dict()


    #-------------------------------------------------------
    def AddEntity(self, name, properties):
        entity = D_Entity(name, properties)
        self.Entities[entity.Id] = entity


    #-------------------------------------------------------
    def GetLinkId(self, parent_id, child_id):
        return self.Links["{}-{}".format(parent_id, child_id)]


    def AddRelationship(self, parent_id, child_id, link_id):
        self.Links["{}-{}".format(parent_id, child_id)] = link_id
        child_entity = self.Entities[child_id]
        parent_entity = self.Entities[parent_id]

        child_entity.RecordParent(parent_entity)
        parent_entity.RecordChild(child_entity)


    #-------------------------------------------------------
    def MakeNetwork(self):
        # loose disconnected entities
        for entity in self.Entities.copy().values():
            if not entity.IsConnected():
                self.Entities.pop(entity.Id)

        self.CreateBundles()
        self.CalcBundleLevels()
        self.AssignNodeLevels()
        return self



## D_Network ###############################################

class D_Network(D_NetworkBuilder):

    #-------------------------------------------------------
    def __init__(self):
        super().__init__()


    #-------------------------------------------------------
    def GetBundle(self, parents):
        id = "-".join(sorted([str(parent.Id) for parent in parents]))
        got = self.Bundles.get(id)

        if got is None:
            name = "-".join(sorted([parent.Name for parent in parents]))
            got = D_Bundle(id, name, parents)
            self.Bundles[id] = got
        
        return got


    #-------------------------------------------------------
    def CreateBundles(self):
        for entity in self.Entities.values():
            entity.CreateBundles(self)
        
        for bundle in self.Bundles.values():
            bundle.SetHierarchy()


    #-------------------------------------------------------
    def CalcBundleLevels(self):
        bundles = self.Bundles.values()
        if not bundles:
            return

        # look at connected bundles first; they're likely to
        # be the most interesting
        for bundle in bundles:
            if bundle.Generation is None and not bundle.HasParents() and bundle.HasChildren():
                bundle.AssignGeneration(0)

        discovered_generations = [bundle.Generation for bundle in bundles if bundle.Generation is not None]
        discovered_generations.append(0)
        min_generation = min(discovered_generations)

        # now add disconnected bundles - at the left of the display
        for bundle in bundles:
            if bundle.Generation is None:
                bundle.AssignGeneration(min_generation)

        for bundle in bundles:
            bundle.SetLevel(min_generation)


    #-------------------------------------------------------
    def AssignNodeLevels(self):
        for entity in self.Entities.values():
            entity.AssignNodeLevel()


    #-------------------------------------------------------
    def GetNumLevels(self):
        return len(set([bundle.Level for bundle in self.Bundles.values()]))

    def GetEntities(self):
        return self.Entities.values()



## G_LayoutConfig ##########################################

class G_LayoutConfig:

    #-------------------------------------------------------
    def __init__(self):
        self.Border = 30
        self.NodeSpacing = 24
        self.NodeWidth = 150
        self.BundleWidth = 14
        self.OutboundBundleSpacing = 6
        self.BallRadius = 4
        self.LinkRadius = 16
        self.MinLevelOffset = 4 * self.LinkRadius
        self.TextOffsetX = 2
        self.TextOffsetY = 6

    #-------------------------------------------------------
    def Extract(self, max_x, max_y):
        return dict(
            Border = self.Border,
            NodeSpacing = self.NodeSpacing,
            NodeWidth = self.NodeWidth,
            BundleWidth = self.BundleWidth,
            OutboundBundleSpacing = self.OutboundBundleSpacing,
            BallRadius = self.BallRadius,
            LinkRadius = self.LinkRadius,
            MinLevelOffset = self.MinLevelOffset,
            TextOffsetX = self.TextOffsetX,
            TextOffsetY = self.TextOffsetY,
            Width = max_x + self.Border,
            Height = max_y + self.Border
        )



## G_LayoutStore ###########################################

class G_LayoutStore:

    #-------------------------------------------------------
    def __init__(self, network):
        self.Network = network
        self.Nodes = dict()


    #-------------------------------------------------------
    def GetNode(self, entity):
        key = entity.Id
        got = self.Nodes.get(key)

        if got is None:
            got = G_Node(entity)
            self.Nodes[key] = got
        
        return got


    #-------------------------------------------------------
    def MakeLink(self, bundle_data, parent, child):
        link_id = self.Network.GetLinkId(parent.Id, child.Id)
        return G_Link(bundle_data, self.GetNode(parent), self.GetNode(child), link_id)



## G_Node ##################################################

class G_Node(Data):
    "Graphical layout data for an Entity"

    #-------------------------------------------------------
    def __init__(self, data):
        self.Data = data
        self.Id = data.Id
        self.Name = data.Name
        data.ChildBundles.sort()


    #-------------------------------------------------------
    def MakeBundles(self, store):
        my_level = self.Data.Level
        return set([G_Bundle(bundle, store) for bundle in self.Data.ChildBundles if bundle.Level == my_level])


    #-------------------------------------------------------
    def AllocateOutboundBundle(self, bundle_data):
        for idx, data in enumerate(self.Data.ChildBundles):
            if data.Id == bundle_data.Id:
                return idx

        return None


    #-------------------------------------------------------
    def Layout(self, pos, config):
        num_bundles = len(self.Data.ChildBundles)
        bundle_height = self.BundleHeight = max(0, num_bundles - 1) * config.OutboundBundleSpacing
        self.X, self.Y = pos
        return (self.X, self.Y + config.NodeSpacing + bundle_height)


    #-------------------------------------------------------
    def Adjust(self, delta):
        self.Y += delta


    #-------------------------------------------------------
    def Extract(self):
        graph = dict(
            x = self.X,
            y = self.Y,
            bundle_height = self.BundleHeight,
            title = self.Data.Name
        )

        graph.update(self.Data.Properties)
        return graph



## G_Bundle ################################################

class G_Bundle(Data):

    #-------------------------------------------------------
    def __init__(self, data, store):
        self.Id = data.Id
        self.Name = data.Name
        self.Data = data
        self.Links = []

        for parent in data.ParentEntities:
            for child in data.ChildEntities:
                self.Links.append(store.MakeLink(data, parent, child))

    #-------------------------------------------------------
    def Layout(self, x, config):
        for link in self.Links:
            link.Layout(x, config)

        return x + config.BundleWidth


    #-------------------------------------------------------
    def Adjust(self, delta, config):
        for link in self.Links:
            delta = link.Adjust(delta, config)

        return delta


    #-------------------------------------------------------
    def Extract(self):
        links =  [link.Extract() for link in self.Links]
        return dict(
            id = str(self),
            links = links
        )



## G_Link ##################################################

class G_Link(Data):
    "Graphical layout data for parent-child relationship line"

    #-------------------------------------------------------
    def __init__(self, bundle_data, parent_node, child_node, link_id):
        self.Name = parent_node.Name + " -> " + child_node.Name
        self.ParentNode = parent_node
        self.ChildNode = child_node
        self.LinkId = link_id
        self.ParentBundleNo = parent_node.AllocateOutboundBundle(bundle_data)


    #-------------------------------------------------------
    def Layout(self, x, config):
        self.X = x
        self.Y = self.ParentBundleNo * config.OutboundBundleSpacing


    #-------------------------------------------------------
    def Adjust(self, delta, config):
        vertical = self.ChildNode.Y - (self.ParentNode.Y + self.Y)
        return max(delta, config.MinLevelOffset - vertical)


    #-------------------------------------------------------
    def Extract(self):
        return dict(
            event_id = self.LinkId,
            px = self.ParentNode.X,
            py = self.ParentNode.Y + self.Y,
            x = self.X,
            cx = self.ChildNode.X,
            cy = self.ChildNode.Y
        )



## Level ###################################################

class Level:
    "Graphical layout for a vertical group of entities"

    #-------------------------------------------------------
    def __init__(self, level):
        self.Level = level
        self.Nodes = []
        self.Bundles = []
        self.IndexLimitNode = None


    #-------------------------------------------------------
    def AddEntity(self, entity, store):
        self.Nodes.append(store.GetNode(entity))


    #-------------------------------------------------------
    def MakeBundles(self, store):
        bundles = set()

        for node in self.Nodes:
            bundles.update(node.MakeBundles(store))

        self.Bundles = sorted([bundle for bundle in bundles])


    #-------------------------------------------------------
    def OrderNodes(self, store):
        my_level = self.Level
        remainder = set(self.Nodes)
        assigned_nodes = set()
        ordered_nodes = []

        def AddNode(node):
            remainder.discard(node)
            if node not in assigned_nodes:
                assigned_nodes.add(node)
                ordered_nodes.append(node)

        # put nodes with non-local children first
        non_local_nodes = dict()
        for node in self.Nodes:
            child_bundles = node.Data.ChildBundles
            if len(child_bundles) != 0:
                max_child_level = max([bundle.Level for bundle in child_bundles])
                if max_child_level != my_level:
                    non_local_nodes.setdefault(max_child_level, []).append(node)

        for key in sorted(non_local_nodes.keys(), reverse = True):
            for node in sorted(non_local_nodes[key]):
                AddNode(node)

        num_nonlocal_nodes = len(ordered_nodes)
                    
        # and the rest in bundle order (keeps a bundle's parents together)
        for bundle in self.Bundles:
            parents = [store.GetNode(parent) for parent in bundle.Data.ParentEntities if parent.Level == my_level]
            for parent in parents:
                AddNode(parent)

        self.Nodes = ordered_nodes
        self.Nodes.extend(sorted([node for node in remainder]))

        if num_nonlocal_nodes != 0:
            self.IndexLimitNode = min(num_nonlocal_nodes, len(self.Nodes) - 1)


    #-------------------------------------------------------
    def Layout(self, pos, config):
        for node in self.Nodes:
            pos = node.Layout(pos, config)

        x, y = pos
        x += config.NodeWidth + config.BundleWidth

        for bundle in reversed(self.Bundles):
            x = bundle.Layout(x, config)

        return (x + config.BundleWidth, y)


    #-------------------------------------------------------
    def Adjust(self, limit, delta, config):
        if limit is not None:
            clip = self.Nodes[0].Y + delta - limit
            if clip < 0:
                delta -= clip

        for node in self.Nodes:
            node.Adjust(delta)

        delta = -1000000
        for bundle in self.Bundles:
            delta = bundle.Adjust(delta, config)

        limit = None
        if self.IndexLimitNode is not None:
            limit = self.Nodes[self.IndexLimitNode].Y + config.NodeSpacing

        return limit, delta


    #-------------------------------------------------------
    def ExtractNodes(self):
        return [node.Extract() for node in self.Nodes]

    def ExtractBundles(self):
        return [bundle.Extract() for bundle in self.Bundles]



## Layout ##################################################

class Layout:

    #-------------------------------------------------------
    def __init__(self, network):
        store = G_LayoutStore(network)
        levels = self.Levels = [Level(i) for i in range(network.GetNumLevels() + 1)]
        for entity in network.GetEntities():
            levels[entity.Level].AddEntity(entity, store)

        for level in levels:
            level.MakeBundles(store)
            level.OrderNodes(store)

        config = self.Config = G_LayoutConfig()
        pos = (config.Border, config.Border)
        for level in levels:
            pos = level.Layout(pos, config)

        limit, delta = None, 0
        for level in levels:
            limit, delta = level.Adjust(limit, delta, config)


    #-------------------------------------------------------
    def Extract(self):
        nodes, bundles = [], []
        for level in self.Levels:
            nodes.extend(level.ExtractNodes())
            bundles.extend(level.ExtractBundles())

        mx = my = 0
        for node in nodes:
            mx = max(mx, node["x"])
            my = max(my, node["y"])

        mx += self.Config.NodeWidth

        config = self.Config.Extract(mx, my)

        data = dict(nodes = nodes, bundles = bundles, config = config)
        return json.dumps(data, sort_keys = True, indent = 4)



## GLOBAL ##################################################

class Tree:

    #-------------------------------------------------------
    def __init__(self):
        self.Builder = D_Network()


    #-------------------------------------------------------
    def AddEntity(self, name, properties):
        self.Builder.AddEntity(name, properties)


    def AddRelationship(self, properties):
        src = properties["source"]
        tgt = properties["target"]
        if src != tgt:
            self.Builder.AddRelationship(src, tgt, properties["event_id"])


    #-------------------------------------------------------
    def Extract(self):
        network = self.Builder.MakeNetwork()
        return Layout(network).Extract()
