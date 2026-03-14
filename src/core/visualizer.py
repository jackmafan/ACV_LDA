import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict

class Visualizer:
    @staticmethod
    def create_sankey_diagram(links: List[Dict], output_path: str = "sankey_diagram.html"):
        """
        Creates a Sankey Diagram from a list of link dictionaries:
        [{'source': 'A_something', 'target': 'C_something', 'value': 0.5}, ...]
        """
        if not links:
            # Create an empty diagram if no links
            fig = go.Figure(go.Sankey(node=dict(label=[]), link=dict(source=[], target=[], value=[])))
            fig.write_html(output_path)
            return output_path

        # 1. Extract all unique nodes
        sources = [link['source'] for link in links]
        targets = [link['target'] for link in links]
        all_nodes = list(set(sources + targets))
        
        # 2. Map nodes to integer indices for Plotly Sankey
        node_to_idx = {node: i for i, node in enumerate(all_nodes)}
        
        # 3. Prepare link data for Plotly
        source_indices = [node_to_idx[link['source']] for link in links]
        target_indices = [node_to_idx[link['target']] for link in links]
        values = [link['value'] for link in links]
        
        # 4. Define nodes
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color="blue"
            ),
            link=dict(
                source=source_indices,
                target=target_indices,
                value=values
            )
        )])
        
        fig.update_layout(title_text="ACV Transition Probability Flow", font_size=12)
        fig.write_html(output_path)
        
        return output_path
