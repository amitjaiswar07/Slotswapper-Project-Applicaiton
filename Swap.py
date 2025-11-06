import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import numpy as np

# Create a network graph representation of the SlotSwapper architecture
G = nx.DiGraph()

# Add nodes with categories for different colors
nodes = [
    # Authentication Flow
    ('User Signup', 'auth'),
    ('Authentication', 'decision'),
    ('Generate JWT', 'auth'),
    ('Store Session', 'auth'),
    ('Dashboard', 'interface'),
    
    # Event Management Flow
    ('Event Mgmt', 'interface'),
    ('Create Events', 'process'),
    ('View Events', 'process'),
    ('Mark Swappable', 'decision'),
    ('Post to Market', 'process'),
    
    # Marketplace Flow
    ('Browse Market', 'interface'),
    ('Find Swap', 'decision'),
    ('Create Request', 'process'),
    
    # Notification Flow
    ('WebSocket Alert', 'notification'),
    ('Recipient Alert', 'notification'),
    ('Accept/Reject', 'decision'),
    
    # Transaction Flow
    ('Begin Transaction', 'transaction'),
    ('Database Lock', 'transaction'),
    ('Validate Swap', 'transaction'),
    ('Validation Check', 'decision'),
    ('Update Events', 'transaction'),
    ('Commit Trans', 'transaction'),
    ('Send Success', 'notification'),
    ('Update Dashboards', 'interface'),
    
    # Error Handling
    ('Rollback', 'error'),
    ('Send Error', 'error'),
    ('Rejection Notice', 'error')
]

# Add all nodes
for node, category in nodes:
    G.add_node(node, category=category)

# Add edges to represent the flow
edges = [
    ('User Signup', 'Authentication'),
    ('Authentication', 'Generate JWT'),
    ('Authentication', 'User Signup'),  # failure loop
    ('Generate JWT', 'Store Session'),
    ('Store Session', 'Dashboard'),
    ('Dashboard', 'Event Mgmt'),
    
    ('Event Mgmt', 'Create Events'),
    ('Event Mgmt', 'View Events'),
    ('Create Events', 'Mark Swappable'),
    ('View Events', 'Mark Swappable'),
    ('Mark Swappable', 'Post to Market'),
    ('Mark Swappable', 'Event Mgmt'),  # no path
    
    ('Post to Market', 'Browse Market'),
    ('Browse Market', 'Find Swap'),
    ('Find Swap', 'Create Request'),
    ('Find Swap', 'Browse Market'),  # no path
    
    ('Create Request', 'WebSocket Alert'),
    ('WebSocket Alert', 'Recipient Alert'),
    ('Recipient Alert', 'Accept/Reject'),
    
    ('Accept/Reject', 'Begin Transaction'),
    ('Accept/Reject', 'Rejection Notice'),
    ('Rejection Notice', 'Browse Market'),
    
    ('Begin Transaction', 'Database Lock'),
    ('Database Lock', 'Validate Swap'),
    ('Validate Swap', 'Validation Check'),
    
    ('Validation Check', 'Update Events'),
    ('Validation Check', 'Rollback'),
    ('Rollback', 'Send Error'),
    ('Send Error', 'Create Request'),
    
    ('Update Events', 'Commit Trans'),
    ('Commit Trans', 'Send Success'),
    ('Send Success', 'Update Dashboards')
]

G.add_edges_from(edges)

# Use hierarchical layout
pos = nx.spring_layout(G, k=3, iterations=50, seed=42)

# Extract node positions
node_x = []
node_y = []
node_text = []
node_colors = []
categories = []

color_map = {
    'auth': '#1FB8CD',
    'decision': '#DB4545', 
    'interface': '#2E8B57',
    'process': '#5D878F',
    'notification': '#D2BA4C',
    'transaction': '#B4413C',
    'error': '#964325'
}

for node in G.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)
    node_text.append(node)
    category = G.nodes[node]['category']
    categories.append(category)
    node_colors.append(color_map[category])

# Extract edges
edge_x = []
edge_y = []
for edge in G.edges():
    x0, y0 = pos[edge[0]]
    x1, y1 = pos[edge[1]]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])

# Create the plot
fig = go.Figure()

# Add edges
fig.add_trace(go.Scatter(x=edge_x, y=edge_y,
                         line=dict(width=2, color='#888'),
                         hoverinfo='none',
                         mode='lines',
                         name='Flow'))

# Add nodes
fig.add_trace(go.Scatter(x=node_x, y=node_y,
                         mode='markers+text',
                         marker=dict(size=20,
                                   color=node_colors,
                                   line=dict(width=2, color='white')),
                         text=node_text,
                         textposition="middle center",
                         textfont=dict(size=10, color='white'),
                         hovertemplate='<b>%{text}</b><extra></extra>',
                         name='Components'))

fig.update_layout(
    title='SlotSwapper System Architecture',
    showlegend=False,
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    plot_bgcolor='rgba(0,0,0,0)',
    annotations=[
        dict(text="Auth Flow", x=-1.2, y=0.8, showarrow=False, font=dict(size=12, color='#1FB8CD')),
        dict(text="Event Mgmt", x=-0.3, y=0.8, showarrow=False, font=dict(size=12, color='#2E8B57')),
        dict(text="Marketplace", x=0.5, y=0.3, showarrow=False, font=dict(size=12, color='#5D878F')),
        dict(text="Transaction", x=0.8, y=-0.5, showarrow=False, font=dict(size=12, color='#B4413C'))
    ]
)

# Save the chart
fig.write_image('slotswapper_architecture.png')
fig.write_image('slotswapper_architecture.svg', format='svg')

print("SlotSwapper system architecture diagram created successfully!")
