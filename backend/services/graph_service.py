import networkx as nx
from sqlalchemy.orm import Session
from models.graph import GlobalNode, GlobalEdge
import json
import logging
from difflib import get_close_matches

logger = logging.getLogger(__name__)

class GraphService:
    def __init__(self, db: Session):
        self.db = db
        self.nx_graph = None  # In-memory graph cache

    def get_node_by_name(self, name: str):
        return self.db.query(GlobalNode).filter(GlobalNode.name == name).first()
        
    def search_nodes_fuzzy(self, query: str, limit: int = 5, cutoff: float = 0.6):
        """Fuzzy search for nodes"""
        all_names = [n[0] for n in self.db.query(GlobalNode.name).all()]
        matches = get_close_matches(query, all_names, n=limit, cutoff=cutoff)
        
        nodes = []
        for name in matches:
            node = self.get_node_by_name(name)
            if node:
                nodes.append(node)
        return nodes

    def add_node(self, name: str, category: str = "Concept", digest: str = "", source_doc_id: str = None):
        """添加或更新节点"""
        node = self.get_node_by_name(name)
        if not node:
            node = GlobalNode(name=name, category=category, digest=digest)
            if source_doc_id:
                node.document_ids = json.dumps([source_doc_id])
            self.db.add(node)
        else:
            # Update existing node
            if digest and len(digest) > len(node.digest or ""):
                node.digest = digest
            
            if source_doc_id:
                docs = json.loads(node.document_ids)
                if source_doc_id not in docs:
                    docs.append(source_doc_id)
                    node.document_ids = json.dumps(docs)
        
        self.db.commit()
        self.db.refresh(node)
        return node

    def add_edge(self, source_name: str, target_name: str, relation: str = "related_to", weight: float = 1.0):
        """添加边 (会自动创建不存在的节点)"""
        source = self.add_node(source_name)
        target = self.add_node(target_name)
        
        # Check if edge exists
        edge = self.db.query(GlobalEdge).filter(
            GlobalEdge.source_id == source.id,
            GlobalEdge.target_id == target.id
        ).first()
        
        if not edge:
            edge = GlobalEdge(
                source_id=source.id,
                target_id=target.id,
                relation=relation,
                weight=weight
            )
            self.db.add(edge)
        else:
            # Strengthen existing connection
            edge.weight += 0.1
            
        self.db.commit()
        return edge

    def build_networkx_graph(self):
        """从数据库构建内存中的NetworkX图"""
        G = nx.DiGraph()
        
        nodes = self.db.query(GlobalNode).all()
        edges = self.db.query(GlobalEdge).all()
        
        for n in nodes:
            G.add_node(n.id, name=n.name, category=n.category, weight=n.weight)
            
        for e in edges:
            G.add_edge(e.source_id, e.target_id, weight=e.weight, relation=e.relation)
            
        self.nx_graph = G
        return G

    def update_pagerank(self):
        """计算PageRank并更新数据库中的节点权重"""
        if not self.nx_graph:
            self.build_networkx_graph()
            
        if len(self.nx_graph.nodes) == 0:
            return
            
        pagerank = nx.pagerank(self.nx_graph, weight='weight')
        
        # Batch update in DB
        for node_id, score in pagerank.items():
            self.db.query(GlobalNode).filter(GlobalNode.id == node_id).update({"weight": score})
            
        self.db.commit()
        logger.info("PageRank updated for all nodes")

    def get_full_graph_data(self):
        """获取用于前端3D可视化的完整数据"""
        nodes = self.db.query(GlobalNode).all()
        edges = self.db.query(GlobalEdge).all()
        
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "val": n.weight * 10,  # Scale for visibility
                    "group": n.category,
                    "desc": n.digest,
                    "docs": json.loads(n.document_ids) if n.document_ids else [] # [NEW] Return source docs
                } for n in nodes
            ],
            "links": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "relation": e.relation
                } for e in edges
            ]
        }

    def find_shortest_path(self, start_name: str, end_name: str):
        """寻找两个概念之间的最短路径"""
        start_node = self.get_node_by_name(start_name)
        end_node = self.get_node_by_name(end_name)
        
        if not start_node or not end_node:
            return None
            
        if not self.nx_graph:
            self.build_networkx_graph()
            
        try:
            path_ids = nx.shortest_path(self.nx_graph, source=start_node.id, target=end_node.id)
            # Convert IDs back to names
            path_names = []
            for nid in path_ids:
                n = self.db.query(GlobalNode).filter(GlobalNode.id == nid).first()
                path_names.append(n.name)
            return path_names
        except nx.NetworkXNoPath:
            return []

    def get_subgraph_context(self, question_entities: list[str], max_hops: int = 1):
        """
        Retrieves a text context based on the subgraph surrounding the question entities.
        Returns: (context_text, context_data_dict)
        """
        if not self.nx_graph:
            self.build_networkx_graph()
            
        context_parts = []
        found_nodes = set()
        
        # 1. Map entities to nodes
        for entity in question_entities:
            # Try exact match first
            node = self.get_node_by_name(entity)
            if not node:
                 # Try fuzzy
                 fuzzy = self.search_nodes_fuzzy(entity, limit=1)
                 if fuzzy:
                     node = fuzzy[0]
            
            if node:
                found_nodes.add(node.id)
                context_parts.append(f"Concept: {node.name} ({node.category})\nSummary: {node.digest or 'N/A'}")
        
        if not found_nodes:
            return "", {"nodes": [], "edges": []}
            
        # 2. Expand to neighbors
        subgraph_nodes = set(found_nodes)
        for node_id in found_nodes:
            if node_id in self.nx_graph:
                # Get neighbors
                neighbors = list(self.nx_graph.neighbors(node_id))
                subgraph_nodes.update(neighbors)
                
                # If we have multiple start nodes, try to find paths between them
                if len(found_nodes) > 1:
                    for other_id in found_nodes:
                        if node_id != other_id:
                            try:
                                path = nx.shortest_path(self.nx_graph, node_id, other_id)
                                subgraph_nodes.update(path)
                            except:
                                pass

        # 3. Construct text from edges in subgraph
        final_edges = []
        context_parts.append("\nRelationships:")
        if len(subgraph_nodes) > 0:
            subgraph = self.nx_graph.subgraph(subgraph_nodes)
            for u, v in subgraph.edges():
                u_node = self.db.query(GlobalNode).filter(GlobalNode.id == u).first()
                v_node = self.db.query(GlobalNode).filter(GlobalNode.id == v).first()
                edge_data = self.nx_graph.get_edge_data(u, v)
                if u_node and v_node:
                    relation = edge_data.get('relation', 'related_to')
                    context_parts.append(f"- {u_node.name} {relation} {v_node.name}")
                    final_edges.append({"source": u, "target": v, "relation": relation})

        context_data = {
            "nodes": list(subgraph_nodes),
            "edges": final_edges
        }
        return "\n".join(context_parts), context_data

    def remove_document_knowledge(self, doc_id: str):
        """
        When a document is deleted:
        1. Find all nodes citing this doc_id.
        2. Remove doc_id from their document_ids list.
        3. If a node has NO other sources, delete the node AND its connected edges.
        """
        # 1. Find potentially affected nodes using LIKE query for efficiency
        # JSON list format: ["id1", "id2"] so we look for "id"
        search_pattern = f'%"{doc_id}"%'
        affected_nodes = self.db.query(GlobalNode).filter(GlobalNode.document_ids.like(search_pattern)).all()
        
        nodes_to_delete = []
        
        for node in affected_nodes:
            try:
                doc_ids = json.loads(node.document_ids or "[]")
                if doc_id in doc_ids:
                    doc_ids.remove(doc_id)
                    
                    if not doc_ids:
                        # No more sources, mark for deletion
                        nodes_to_delete.append(node.id)
                    else:
                        # Update with remaining sources
                        node.document_ids = json.dumps(doc_ids)
            except json.JSONDecodeError:
                continue
                
        if nodes_to_delete:
            # 2. Delete edges connected to these nodes
            self.db.query(GlobalEdge).filter(
                (GlobalEdge.source_id.in_(nodes_to_delete)) | 
                (GlobalEdge.target_id.in_(nodes_to_delete))
            ).delete(synchronize_session=False)
            
            # 3. Delete the nodes
            self.db.query(GlobalNode).filter(GlobalNode.id.in_(nodes_to_delete)).delete(synchronize_session=False)
            
            logger.info(f"🗑️ [Graph Cleanup] Deleted {len(nodes_to_delete)} nodes orphaned by file {doc_id}")
        
        self.db.commit()
