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
    def __init__(self, properties):
        self.Properties = properties
        self.Id = properties["event_id"]
        self.Name = properties["title"]

        self.ParentEntities = []
        self.ChildEntities = []
        self.ParentBundle = None
        self.ChildBundles = []
        self.Level = -1


    #-------------------------------------------------------
    def RecordParent(self, parent_entity):
        self.ParentEntities.append(parent_entity)


    #-------------------------------------------------------
    def RecordChild(self, child_entity):
        self.ChildEntities.append(child_entity)


    #-------------------------------------------------------
    def HasParents(self):
        return len(self.ParentEntities) != 0

    def CreateBundles(self, network):
        if self.HasParents():
            bundle = self.ParentBundle = network.GetBundle(self.ParentEntities)
            bundle.AddChildEntity(self)

    def RecordChildBundle(self, bundle):
        self.ChildBundles.append(bundle)


    #-------------------------------------------------------
    def AssignNodeLevel(self, level):
        if level > self.Level:
            self.Level = level



## D_Bundle ################################################

class D_Bundle(Data):
    "Graphical layout data for a group of Links - a bundle of vertical connections"

    #-------------------------------------------------------
    def __init__(self, id, name, parents):
        self.Generation = None
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
        parent_bundles = self.ParentBundles = [parent.ParentBundle for parent in self.ParentEntities if parent.ParentBundle is not None]
        for bundle in parent_bundles:
            bundle.ChildBundles.append(self)

        for parent in self.ParentEntities:
            parent.RecordChildBundle(self)


    #-------------------------------------------------------
    def HasChildren(self):
        return len(self.ChildBundles) != 0

    def HasParents(self):
        return len(self.ParentBundles) != 0

    def IsRootBundle(self):
        # if we have a generation number, then we've already been assigned
        # to another (disjoint) network of bundles - and so, cannot be a new
        # root
        return not self.HasParents() and self.HasChildren() and not self.HasGeneration()


    #-------------------------------------------------------
    def HasGeneration(self):
        return self.Generation is not None

    def SetGeneration(self, generation):
        # Note - only works for networks where all parent bundles
        # belong to the same generation
        if self.HasGeneration():
            return False
        else:
            self.Generation = generation
            return True


    #-------------------------------------------------------
    def AssignAncestorGeneration(self, generation):
        for parent in self.ParentBundles:
            parent.AssignGeneration(generation - 1)

    def AssignDescendentGeneration(self, generation):
        for child in self.ChildBundles:
            child.AssignGeneration(generation + 1)

    def AssignGeneration(self, generation):
        if self.SetGeneration(generation):
            self.AssignAncestorGeneration(generation)
            self.AssignDescendentGeneration(generation)

    def AssignDefaultGeneration(self):
        self.SetGeneration(0)


    #-------------------------------------------------------
    def AssignNodeLevels(self, level_offset):
        level = self.Generation + level_offset
        for parent in self.ParentEntities:
            parent.AssignNodeLevel(level)

        for child in self.ChildEntities:
            child.AssignNodeLevel(level + 1)



## D_NetworkBuilder ########################################

class D_NetworkBuilder:

    #-------------------------------------------------------
    def __init__(self):
        self.Entities = dict()
        self.Links = dict()
        self.Bundles = dict()


    #-------------------------------------------------------
    def AddEntity(self, properties):
        entity = D_Entity(properties)
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
        self.CreateBundles()
        self.AssignNodeLevels()
        return self



## D_Network ###############################################

class D_Network(D_NetworkBuilder):

    #-------------------------------------------------------
    def __init__(self):
        super().__init__()


    #-------------------------------------------------------
    def GetBundle(self, parents):
        id = "-".join([str(parent.Id) for parent in parents])
        got = self.Bundles.get(id)

        if got is None:
            name = "-".join([parent.Name for parent in parents])
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
    def AssignNodeLevels(self):
        # assign bundles generations first
        for bundle in self.Bundles.values():
            if bundle.IsRootBundle():
                bundle.AssignGeneration(0)

        # assign default generation for any bundles not covered
        for bundle in self.Bundles.values():
            bundle.AssignDefaultGeneration()

        # then build bundle generations into a "list"
        generations = dict()
        for bundle in self.Bundles.values():
            generation = bundle.Generation
            if generation in generations:
                generations[generation].append(bundle)
            else:
                generations[generation] = [bundle]

        # translate that to node levels
        indices = [key for key in generations.keys()]
        self.NumLevels = len(indices)
        if self.NumLevels > 0:
            indices.sort()
            level_offset = - indices[0]

            for index in indices:
                bundles = generations[index]
                for bundle in bundles:
                    bundle.AssignNodeLevels(level_offset)


    #-------------------------------------------------------
    def GetNumLevels(self):
        return self.NumLevels

    def GetEntities(self):
        return [entity for entity in self.Entities.values() if entity.Level >= 0]



## G_LayoutConfig ##########################################

class G_LayoutConfig:

    #-------------------------------------------------------
    def __init__(self):
        self.Border = 30
        self.NodeSpacing = 22
        self.NodeWidth = 150
        self.BundleWidth = 14
        self.OutboundBundleSpacing = 4
        self.BallRadius = 4
        self.LinkRadius = 16
        self.MinLevelOffset = 3 * self.LinkRadius
        self.TextOffsetX = 2
        self.TextOffsetY = 4

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
        return set([G_Bundle(bundle, store) for bundle in self.Data.ChildBundles])


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
            bundle_height = self.BundleHeight
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
    def __init__(self):
        self.Nodes = []
        self.Bundles = []


    #-------------------------------------------------------
    def AddEntity(self, entity, store):
        self.Nodes.append(store.GetNode(entity))


    #-------------------------------------------------------
    def MakeBundles(self, store):
        bundles = set()
        for node in self.Nodes:
            bundles.update(node.MakeBundles(store))

        self.Bundles = sorted([bundle for bundle in bundles])

        # remake nodes in bundle order
        remainder = set(self.Nodes)
        nodes = set()
        self.Nodes = []
        for bundle in self.Bundles:
            parents = [store.GetNode(parent) for parent in  bundle.Data.ParentEntities]
            for parent in parents:
                remainder.discard(parent)
                if parent not in nodes:
                    nodes.add(parent)
                    self.Nodes.append(parent)

        self.Nodes.extend(sorted([node for node in remainder]))


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
    def Adjust(self, delta, config):
        for node in self.Nodes:
            node.Adjust(delta)

        delta = -1000000
        for bundle in self.Bundles:
            delta = bundle.Adjust(delta, config)

        return delta


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
        levels = self.Levels = [Level() for i in range(network.GetNumLevels() + 1)]
        for entity in network.GetEntities():
            levels[entity.Level].AddEntity(entity, store)

        for level in levels:
            level.MakeBundles(store)

        config = self.Config = G_LayoutConfig()
        pos = (config.Border, config.Border)
        for level in levels:
            pos = level.Layout(pos, config)


        delta = 0
        for level in levels:
            delta = level.Adjust(delta, config)


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
    def AddEntity(self, properties):
        self.Builder.AddEntity(properties)


    def AddRelationship(self, properties):
        self.Builder.AddRelationship(properties["source"], properties["target"], properties["event_id"])


    #-------------------------------------------------------
    def Extract(self):
        network = self.Builder.MakeNetwork()
        return Layout(network).Extract()
