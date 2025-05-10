# huawei_tools = [
#     {
#         "type": "function",
#         "name": "list_clusters",
#         "description": "List all clusters in a Huawei CCE project.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region to list clusters in"},
#                 "project_id": {"type": "string", "description": "Project ID to list clusters for"}
#             },
#             "required": ["region", "project_id"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "get_cluster_by_id",
#         "description": "Get a specific cluster by ID.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region of the cluster"},
#                 "project_id": {"type": "string", "description": "Project ID"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"}
#             },
#             "required": ["region", "project_id", "cluster_id"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "list_namespaces",
#         "description": "List all namespaces in a Huawei CCE cluster.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"}
#             },
#             "required": ["region", "cluster_id"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "get_namespace_by_name",
#         "description": "Get a namespace in a Huawei CCE cluster by name.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"},
#                 "name": {"type": "string", "description": "name"}
#             },
#             "required": ["region", "cluster_id", "name"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "create_namespace",
#         "description": "Create a namespace in a Huawei CCE cluster.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"},
#                 "name": {"type": "string", "description": "name"}
#             },
#             "required": ["region", "cluster_id", "name"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "delete_namespace",
#         "description": "Delete a namespace in a Huawei CCE cluster.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"},
#                 "name": {"type": "string", "description": "name"}
#             },
#             "required": ["region", "cluster_id", "name"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "list_pods",
#         "description": "List all pods in a Huawei CCE cluster.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"}
#             },
#             "required": ["region", "cluster_id"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "list_pods_by_namespace",
#         "description": "List all pods in a namespace in a Huawei CCE cluster.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"},
#                 "namespace": {"type": "string", "description": "Namespace"}
#             },
#             "required": ["region", "cluster_id", "namespace"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "get_pod_by_name_and_namespace",
#         "description": "Get a specific pod in a Huawei CCE cluster by name and namespace.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"},
#                 "namespace": {"type": "string", "description": "Namespace"},
#                 "pod_name": {"type": "string", "description": "Pod name"}
#             },
#             "required": ["region", "cluster_id", "namespace", "pod_name"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "create_pod",
#         "description": "Create a pod in a Huawei CCE cluster.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"},
#                 "namespace": {"type": "string", "description": "Namespace"},
#                 "pod_name": {"type": "string", "description": "Pod name"},
#                 "container_name": {"type": "string", "description": "Container name"},
#                 "image": {"type": "string", "description": "Container image"}
#             },
#             "required": ["region", "cluster_id", "namespace", "pod_name", "container_name", "image"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "delete_pod",
#         "description": "Delete a pod by name and namespace in a Huawei CCE cluster.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"},
#                 "namespace": {"type": "string", "description": "Namespace"},
#                 "pod_name": {"type": "string", "description": "Pod name"}
#             },
#             "required": ["region", "cluster_id", "namespace", "pod_name"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "delete_pods_by_namespace",
#         "description": "Delete all pods in a namespace in a Huawei CCE cluster.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "region": {"type": "string", "description": "Region"},
#                 "cluster_id": {"type": "string", "description": "Cluster ID"},
#                 "namespace": {"type": "string", "description": "Namespace"}
#             },
#             "required": ["region", "cluster_id", "namespace"],
#             "additionalProperties": False
#         }
#     }
# ]


# weather_tools = [{
#     "type": "function",
#     "name": "get_weather",
#     "description": "Get current temperature for a given location.",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "location": {
#                 "type": "string",
#                 "description": "City and country e.g. Bogotá, Colombia"
#             }
#         },
#         "required": [
#             "location"
#         ],
#         "additionalProperties": False
#     }
# }]



# server_weather_tools = [
#     {
#         "type": "function",
#         "name": "get_alerts",
#         "description": "Get weather alerts for a US state.\n\nArgs:\n    state: Two-letter US state code (e.g. CA, NY)",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "state": {
#                     "type": "string",
#                     "description": "Two-letter US state code (e.g. CA, NY)"
#                 }
#             },
#             "required": ["state"],
#             "additionalProperties": False
#         }
#     },
#     {
#         "type": "function",
#         "name": "get_forecast",
#         "description": "Get weather forecast for a location.\n\nArgs:\n    latitude: Latitude of the location\n    longitude: Longitude of the location",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "latitude": {
#                     "type": "number",
#                     "description": "Latitude of the location"
#                 },
#                 "longitude": {
#                     "type": "number",
#                     "description": "Longitude of the location"
#                 }
#             },
#             "required": ["latitude", "longitude"],
#             "additionalProperties": False
#         }
#     }
# ]
