import json
import hashlib
import copy

### UTIL ###


def get_module_additional_data(module_name, id, additional_data):
    if module_name not in additional_data:
        return {}
    if id not in additional_data[module_name]:
        return {}
    return additional_data[module_name][id]


def bigger_than_zero(attributes, arg=None, additional_data=None):
    value = attributes.get(arg, None)
    if value > 0:
        return value
    return None


def clean_empty_values_single_dict(value):
    result = {}
    for k, v in value.items():
        if v or v == 0:
            result[k] = v
    return result


def clean_json_values(value, remove_zero=False, exclude_keys=None):
    if exclude_keys is None:
        exclude_keys = ["tags"]

    if remove_zero:
        empty_values = ["", None, [], {}, 0]
    else:
        empty_values = ["", None, [], {}]

    if isinstance(value, dict):
        keys_to_delete = []
        for key, val in value.items():
            # Skip cleaning for keys in the exclude_keys list
            if key in exclude_keys:
                continue

            if val in empty_values:
                keys_to_delete.append(key)
            else:
                value[key] = clean_json_values(val, remove_zero, exclude_keys)
        for key in keys_to_delete:
            if key not in exclude_keys:  # Double-check to avoid deleting excluded keys
                del value[key]
    elif isinstance(value, list):
        value[:] = [clean_json_values(item, remove_zero, exclude_keys)
                    for item in value if item not in empty_values]
        value[:] = [item for item in value if item not in empty_values]
    return value


def clean_empty_values_dict(attributes, arg=None, additional_data=None):
    value = attributes.get(arg, None)
    value = clean_json_values(value=value)
    return value


def clean_empty_values_list(attributes, arg=None, additional_data=None):
    values = attributes.get(arg, None)
    result = []
    for value in values:
        value = clean_json_values(value=value)
        result.append(value)
    return result

#### IAM ####


def get_policy_attachment_index(attributes, arg=None, additional_data=None):
    role = attributes.get('role')
    policy_name = attributes.get('policy_arn').split('/')[-1]
    return role+"_"+policy_name


def get_inline_policies(attributes, arg=None, additional_data=None):
    # convert data_dict to str
    inline_policy = attributes.get("inline_policy")
    for policy in inline_policy:
        policy_str = json.dumps(policy["policy"])
        policy_str = policy_str.replace('${', '$${')
        policy["policy"] = json.loads(policy_str)
    return inline_policy


def get_instance_profiles(attributes, arg=None, additional_data=None):
    name = attributes.get("name")
    tags = attributes.get("tags")
    result = [{"name": name, "tags": tags}]
    path = attributes.get("path")
    if path != "/":
        result[0]["path"] = path
    return result


def get_policy_documents(attributes, arg=None, additional_data=None):
    # convert data_dict to str
    policy_documents = attributes.get("policy")
    policy_documents_dict = json.loads(policy_documents)
    # check if policy_documents_dict["Statement"] is a list
    if not isinstance(policy_documents_dict["Statement"], list):
        policy_documents_dict["Statement"] = [
            policy_documents_dict["Statement"]]
    # use policy_documents_dict for result
    result = json.dumps(policy_documents_dict)
    result = result.replace('${', '$${')
    # convert data_str back to dict
    return result


def iam_get_managed_policy_arns(attributes, arg=None, additional_data=None):
    policy_arns = attributes.get("managed_policy_arns")
    result = {}
    for policy_arn in policy_arns:
        policy_name = policy_arn.split('/')[-1]
        result[policy_name] = policy_arn
    return result

#### SECURITY GROUP ####


def get_security_group_rules(attributes, arg=None, additional_data=None):
    key = attributes["id"]
    result = {key: {}}
    for k in attributes.keys():
        if k not in ["from_port", "to_port", "ip_protocol", "description", "cidr_ipv4", "cidr_ipv6", "prefix_list_id", "referenced_security_group_id", "tags"]:
            continue
        val = attributes.get(k)
        if not val and val != 0 and k != "description":
            continue
        if k == "referenced_security_group_id":
            security_group_id = attributes.get("security_group_id")
            if security_group_id == val:
                result[key][k] = "self"
                continue
        result[key][k] = val
    return result


def get_vpc_id(attributes, arg=None, additional_data=None):
    vpc_name = get_vpc_name(attributes, arg, additional_data)
    if not vpc_name:
        return attributes.get(arg)
    return ""


def get_vpc_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_security_group", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name

### KMS ###


def build_aliases(attributes, arg=None, additional_data=None):
    name = attributes.get(arg)
    return [name]


def build_grants(attributes, arg=None, additional_data=None):
    key = attributes.get("id")
    # hash the key and get the last 8 chars
    # key = hashlib.sha256(key.encode()).hexdigest()[:8]
    # key = "grant_"+key

    result = {key: {}}
    name = attributes.get("name")
    grantee_principal = attributes.get("grantee_principal")
    operations = attributes.get("operations")
    constraints = attributes.get("constraints")
    retiring_principal = attributes.get("retiring_principal")
    grant_creation_tokens = attributes.get("grant_creation_tokens")
    retire_on_delete = attributes.get("retire_on_delete")
    result[key]["name"] = name
    result[key]["grantee_principal"] = grantee_principal
    result[key]["operations"] = operations
    result[key]["constraints"] = constraints
    result[key]["retiring_principal"] = retiring_principal
    result[key]["grant_creation_tokens"] = grant_creation_tokens
    result[key]["retire_on_delete"] = retire_on_delete
    return result

### CODEARTIFACT ###


def codeartifact_build_repositories(attributes, arg=None, additional_data=None):
    result = {}
    repository = attributes.get("repository")
    result[repository] = {}
    description = attributes.get("description")
    if description:
        result[repository]["description"] = description
    external_connections = attributes.get("external_connections")
    if external_connections:
        for index, external_connection in enumerate(external_connections):
            del external_connections[index]['package_format']
            del external_connections[index]['status']
        result[repository]["external_connections"] = external_connections
    upstream = attributes.get("upstream")
    if upstream:
        result[repository]["upstream"] = upstream
    tags = attributes.get("tags")
    if tags:
        result[repository]["tags"] = tags

    return result


def codeartifact_build_repositories_policy(attributes, arg=None, additional_data=None):
    result = {}
    repository = attributes.get("repository")
    result[repository] = {}
    policy_document = attributes.get("policy_document")
    if policy_document:
        result[repository]["policy_document"] = policy_document

    return result


def code_artifact_get_encryption_key_alias(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "codeartifact", id, additional_data)
    alias = ""
    if instance_data:
        alias = instance_data.get("kms_key_alias", "")
    return alias


def code_artifact_get_encryption_key(attributes, arg=None, additional_data=None):
    kms_key_id = attributes.get("encryption_key")
    alias = code_artifact_get_encryption_key_alias(
        attributes, arg, additional_data)
    if alias:
        return ""
    return kms_key_id


### ACM ###
def get_field_from_attrs(attributes, arg=None, additional_data=None):
    keys = arg.split(".")
    result = attributes
    for key in keys:
        if isinstance(result, list):
            result = [sub_result.get(key, None) if isinstance(
                sub_result, dict) else None for sub_result in result]
            if len(result) == 1:
                result = result[0]
        else:
            result = result.get(key, None)
        if result in ["", None]:
            return None
    return result


def acm_get_validation_method(attributes, arg=None, additional_data=None):
    validation_method = attributes.get("validation_method", None)
    if validation_method == "NONE":
        return None
    return validation_method


### ELBV2 ###
def get_listeners_elbv2(attributes, arg=None, additional_data=None):
    port = attributes.get('port')
    default_actions = attributes.get('default_action')
    for default_action in default_actions:
        # if default_action.order is 0 remove corder key
        if default_action.get('order') == 0:
            del default_action['order']
        forward = default_action.get('forward')
        if forward:
            load_balancer_type = attributes.get('load_balancer_type')
            if load_balancer_type == "network":
                del default_action['forward']
            stickiness = forward[0].get('stickiness')
            if stickiness:
                if stickiness[0].get('duration') == 0:
                    del default_action['forward'][0]['stickiness']
            del default_action['target_group_arn']

    listener = {
        'port': port,
        'protocol': attributes.get('protocol'),
        'ssl_policy': attributes.get('ssl_policy'),
        'certificate_arn': attributes.get('certificate_arn'),
        'default_action': default_actions,
        'tags': attributes.get('tags'),
    }

    listener = clean_json_values(value=listener)

    return {port: listener}


def get_port_elbv2(attributes, arg=None, additional_data=None):
    return str(attributes.get('port'))

# def get_listener_certificate_elbv2(attributes, arg=None, additional_data=None):
#     listener_arn = attributes.get('listener_arn')
#     # Get the port of the listener
#     response_listener = aws_clients.elbv2_client.describe_listeners(
#         ListenerArns=[listener_arn]
#     )
#     listener_port = response_listener['Listeners'][0]['Port']

#     certificate_arn = attributes.get('certificate_arn')
#     if certificate_arn:
#         # Get the domain name for the certificate
#         response = aws_clients.acm_client.describe_certificate(
#             CertificateArn=certificate_arn)

#     return self.listeners

# def get_port_domain_name_elbv2(attributes, arg=None, additional_data=None):
#     listener_arn = attributes.get('listener_arn')

#     # Get the port of the listener
#     response_listener = aws_clients.elbv2_client.describe_listeners(
#         ListenerArns=[listener_arn]
#     )
#     listener_port = response_listener['Listeners'][0]['Port']

#     domain_name = ""
#     if attributes.get('certificate_arn'):
#         # Use the ACM client
#         response = aws_clients.acm_client.describe_certificate(
#             CertificateArn=attributes.get('certificate_arn')
#         )
#         domain_name = response['Certificate']['DomainName']

#     # Return in the format 'port-domain_name'
#     return f"{listener_port}-{domain_name}"


def get_subnet_names_elbv2(attributes, arg=None, additional_data=None):
    id = attributes.get('id')
    instance_data = get_module_additional_data("aws_lb", id, additional_data)
    return instance_data.get("subnet_names", [])


def get_subnet_ids_elbv2(attributes, arg=None, additional_data=None):
    subnet_names = get_subnet_names_elbv2(attributes, arg, additional_data)
    if subnet_names:
        return ""
    else:
        return attributes.get(arg)


def get_vpc_name_elbv2(attributes, arg=None, additional_data=None):
    id = attributes.get('id')
    instance_data = get_module_additional_data("aws_lb", id, additional_data)
    return instance_data.get("vpc_name", "")


def get_vpc_id_elbv2(attributes, arg=None, additional_data=None):
    vpc_name = get_vpc_name_elbv2(attributes, arg, additional_data)
    if not vpc_name:
        return attributes.get(arg)
    else:
        return ""

### APIGATEWAY ###


def apigateway_openapi_spec(attributes, arg=None, additional_data=None):
    id = attributes.get('id')
    instance_data = get_module_additional_data(
        "aws_api_gateway_rest_api", id, additional_data)
    return instance_data.get('openapi_spec_file', "")


def apigateway_build_resources(attributes, arg=None, additional_data=None):
    result = {}
    path = attributes.get('path')
    path_part = attributes.get('path_part')

    parent_path_part = "/".join(path.split('/')[:-1])
    if parent_path_part == '':
        parent_path_part = "/"

    # calculate the depth by looking at the number of slashes in the path
    if path == '/':
        depth = 0
        parent_path_part = ""
    else:
        depth = path.count('/')

    result[path] = {}
    result[path]['parent_path_part'] = parent_path_part
    result[path]['depth'] = depth
    result[path]['path_part'] = path_part

    return result


def apigateway_build_methods(attributes, arg=None, additional_data=None):
    result = {}
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    http_method = attributes.get('http_method')
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')
    # path = aws_clients.apigateway_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)['path']
    result[path] = {'methods': {}}
    result[path]['methods'][http_method] = {}
    result[path]['methods'][http_method]['authorization'] = attributes.get(
        'authorization')
    result[path]['methods'][http_method]['authorizer_id'] = attributes.get(
        'authorizer_id')
    result[path]['methods'][http_method]['authorization_scopes'] = attributes.get(
        'authorization_scopes')
    result[path]['methods'][http_method]['api_key_required'] = attributes.get(
        'api_key_required')
    result[path]['methods'][http_method]['operation_name'] = attributes.get(
        'operation_name')
    result[path]['methods'][http_method]['request_models'] = attributes.get(
        'request_models')
    result[path]['methods'][http_method]['request_validator_id'] = attributes.get(
        'request_validator_id')
    result[path]['methods'][http_method]['request_parameters'] = attributes.get(
        'request_parameters')

    result = clean_json_values(value=result)

    return result


def apigateway_build_integrations(attributes, arg=None, additional_data=None):
    result = {}
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    http_method = attributes.get('http_method')
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')
    result[path] = {'methods': {}}
    result[path]['methods'][http_method] = {"integration": {}}
    result[path]['methods'][http_method]['integration']['integration_http_method'] = attributes.get(
        'integration_http_method')
    result[path]['methods'][http_method]['integration']['type'] = attributes.get(
        'type')
    result[path]['methods'][http_method]['integration']['connection_type'] = attributes.get(
        'connection_type')
    result[path]['methods'][http_method]['integration']['connection_id'] = attributes.get(
        'connection_id')
    result[path]['methods'][http_method]['integration']['uri'] = attributes.get(
        'uri')
    result[path]['methods'][http_method]['integration']['credentials'] = attributes.get(
        'credentials')
    result[path]['methods'][http_method]['integration']['request_templates'] = attributes.get(
        'request_templates')
    result[path]['methods'][http_method]['integration']['request_parameters'] = attributes.get(
        'request_parameters')
    result[path]['methods'][http_method]['integration']['passthrough_behavior'] = attributes.get(
        'passthrough_behavior')
    result[path]['methods'][http_method]['integration']['cache_key_parameters'] = attributes.get(
        'cache_key_parameters')
    result[path]['methods'][http_method]['integration']['cache_namespace'] = attributes.get(
        'cache_namespace')
    result[path]['methods'][http_method]['integration']['content_handling'] = attributes.get(
        'content_handling')
    result[path]['methods'][http_method]['integration']['timeout_milliseconds'] = attributes.get(
        'timeout_milliseconds')
    result[path]['methods'][http_method]['integration']['tls_config'] = attributes.get(
        'tls_config')

    result = clean_json_values(value=result)

    return result


def apigateway_build_method_responses(attributes, arg=None, additional_data=None):
    result = {}
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    http_method = attributes.get('http_method')
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')
    result[path] = {'methods': {}}
    result[path]['methods'][http_method] = {"method_responses": {}}
    result[path]['methods'][http_method]['method_responses'][attributes.get(
        'status_code')] = {}
    result[path]['methods'][http_method]['method_responses'][attributes.get(
        'status_code')]['response_models'] = attributes.get('response_models')
    result[path]['methods'][http_method]['method_responses'][attributes.get(
        'status_code')]['response_parameters'] = attributes.get('response_parameters')

    result = clean_json_values(value=result)

    return result


def apigateway_build_integration_responses(attributes, arg=None, additional_data=None):
    result = {}
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    http_method = attributes.get('http_method')
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')
    result[path] = {'methods': {}}
    result[path]['methods'][http_method] = {"integration": {}}
    result[path]['methods'][http_method]['integration']['responses'] = {}
    result[path]['methods'][http_method]['integration']['responses'][attributes.get(
        'status_code')] = {}
    result[path]['methods'][http_method]['integration']['responses'][attributes.get(
        'status_code')]['response_templates'] = attributes.get('response_templates')
    result[path]['methods'][http_method]['integration']['responses'][attributes.get(
        'status_code')]['response_parameters'] = attributes.get('response_parameters')
    result[path]['methods'][http_method]['integration']['responses'][attributes.get(
        'status_code')]['content_handling'] = attributes.get('content_handling')
    result[path]['methods'][http_method]['integration']['responses'][attributes.get(
        'status_code')]['selection_pattern'] = attributes.get('selection_pattern')

    result = clean_json_values(value=result)

    return result


def apigateway_target_resource_name(attributes, arg=None, additional_data=None):
    path = attributes.get('path')
    if path == '/':
        depth = 0
    else:
        depth = path.count('/')

    return "depth_"+str(depth)


def apigateway_target_method_name(attributes, arg=None, additional_data=None):
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    # get path for resource
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')
    # path = aws_clients.apigateway_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)['path']
    if path == '/':
        depth = 0
    else:
        depth = path.count('/')

    return "depth_"+str(depth)


def apigateway_target_integration_name(attributes, arg=None, additional_data=None):
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    # get path for resource
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')
    # path = aws_clients.apigateway_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)['path']
    if path == '/':
        depth = 0
    else:
        depth = path.count('/')

    return "depth_"+str(depth)


def apigateway_method_index(attributes, arg=None, additional_data=None):
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    # Get the resource path
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')

    # path = aws_clients.apigateway_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)['path']
    http_method = attributes.get('http_method')
    return f"{path}/{http_method}"


def apigateway_integration_index(attributes, arg=None, additional_data=None):
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    # Get the resource path
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')

    # path = aws_clients.apigateway_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)['path']
    http_method = attributes.get('http_method')
    return f"{path}/{http_method}"


def apigateway_method_response_index(attributes, arg=None, additional_data=None):
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    # Get the resource path
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')

    # path = aws_clients.apigateway_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)['path']
    http_method = attributes.get('http_method')
    return f"{path}/{http_method}/{attributes.get('status_code')}"


def apigateway_integration_response_index(attributes, arg=None, additional_data=None):
    # rest_api_id = attributes.get('rest_api_id')
    resource_id = attributes.get('resource_id')
    # Get the resource path
    instance_data = get_module_additional_data(
        "aws_api_gateway_resource", resource_id, additional_data)
    path = instance_data.get('path')

    # path = aws_clients.apigateway_client.get_resource(restApiId=rest_api_id, resourceId=resource_id)['path']
    http_method = attributes.get('http_method')
    return f"{path}/{http_method}/{attributes.get('status_code')}"


def apigateway_deployment_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['rest_api_id']}/{attributes['id']}"


def apigateway_resource_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['rest_api_id']}/{attributes['id']}"


def apigateway_method_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['rest_api_id']}/{attributes['resource_id']}/{attributes['http_method']}"


def apigateway_integration_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['rest_api_id']}/{attributes['resource_id']}/{attributes['http_method']}"


def apigateway_method_response_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['rest_api_id']}/{attributes['resource_id']}/{attributes['http_method']}/{attributes['status_code']}"


def apigateway_integration_response_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['rest_api_id']}/{attributes['resource_id']}/{attributes['http_method']}/{attributes['status_code']}"


def apigateway_gateway_response_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['rest_api_id']}/{attributes['response_type']}"


def apigateway_model_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['rest_api_id']}/{attributes['name']}"


def apigateway_build_models(attributes, arg=None, additional_data=None):
    result = {}
    name = attributes.get('name')
    result[name] = {}
    result[name]['content_type'] = attributes.get('content_type')
    result[name]['description'] = attributes.get('description')
    result[name]['schema'] = attributes.get('schema')

    result = clean_json_values(value=result)

    return result


def apigateway_build_gateway_responses(attributes, arg=None, additional_data=None):
    result = {}
    response_type = attributes.get('response_type')
    result[response_type] = {}
    result[response_type]['status_code'] = attributes.get('status_code')
    result[response_type]['response_templates'] = attributes.get(
        'response_templates')
    result[response_type]['response_parameters'] = attributes.get(
        'response_parameters')

    result = clean_json_values(value=result)

    return result


def apigateway_get_method_settings(attributes, arg=None, additional_data=None):
    stage_name = attributes['stage_name']
    method_path = attributes['method_path']
    return f"{stage_name}/{method_path}"


def apigateway_build_method_settings(attributes, arg=None, additional_data=None):
    result = {}
    stage_name = attributes['stage_name']
    method_path = attributes['method_path']
    key = f"{stage_name}/{method_path}"
    result[key] = {}
    result[key]['stage_name'] = stage_name
    result[key]['method_path'] = method_path
    settings = attributes.get('settings')
    if settings:
        result[key]['cache_data_encrypted'] = settings[0].get(
            'cache_data_encrypted')
        result[key]['cache_ttl_in_seconds'] = settings[0].get(
            'cache_ttl_in_seconds')
        result[key]['caching_enabled'] = settings[0].get('caching_enabled')
        result[key]['data_trace_enabled'] = settings[0].get(
            'data_trace_enabled')
        result[key]['logging_level'] = settings[0].get('logging_level')
        result[key]['metrics_enabled'] = settings[0].get('metrics_enabled')
        result[key]['require_authorization_for_cache_control'] = settings[0].get(
            'require_authorization_for_cache_control')
        result[key]['throttling_burst_limit'] = settings[0].get(
            'throttling_burst_limit')
        result[key]['throttling_rate_limit'] = settings[0].get(
            'throttling_rate_limit')
        result[key]['unauthorized_cache_control_header_strategy'] = settings[0].get(
            'unauthorized_cache_control_header_strategy')

    result = clean_json_values(value=result)

    return result


def apigateway_get_stage_name_index(attributes, arg=None, additional_data=None):
    stage_name = attributes['stage_name']
    deployment_id = attributes['deployment_id']
    return f"{deployment_id}-{stage_name}"


def apigateway_build_stages(attributes, arg=None, additional_data=None):
    stage_name = attributes['stage_name']
    deployment_id = attributes['deployment_id']
    result = {}
    if deployment_id not in result:
        result[deployment_id] = {'stages': {}}
    result[deployment_id]['stages'][stage_name] = {}
    result[deployment_id]['stages'][stage_name]['xray_tracing_enabled'] = attributes.get(
        'xray_tracing_enabled')
    result[deployment_id]['stages'][stage_name]['cache_cluster_enabled'] = attributes.get(
        'cache_cluster_enabled')
    tmp = attributes.get('cache_cluster_size')
    if tmp:
        result[deployment_id]['stages'][stage_name]['cache_cluster_size'] = tmp
    tmp = attributes.get('description')
    if tmp:
        result[deployment_id]['stages'][stage_name]['description'] = tmp
    tmp = attributes.get('tags')
    if tmp:
        result[deployment_id]['stages'][stage_name]['tags'] = tmp
    tmp = attributes.get('variables')
    if tmp:
        result[deployment_id]['stages'][stage_name]['variables'] = tmp
    tmp = attributes.get('access_log_settings')
    if tmp:
        result[deployment_id]['stages'][stage_name]['access_log_settings'] = tmp

    result = clean_json_values(value=result)

    return result


def apigateway_build_deployments(attributes, arg=None, additional_data=None):
    deployment_id = attributes['id']
    result = {}
    if deployment_id not in result:
        result[deployment_id] = {}
    result[deployment_id]['description'] = attributes.get('description')

    result = clean_json_values(value=result)
    return result


def apigateway_build_base_path_mappings(attributes, arg=None, additional_data=None):
    result = {}
    domain_name = attributes.get('domain_name')+"_"
    result[domain_name] = {}
    result[domain_name]['domain_name'] = attributes.get('domain_name')
    result[domain_name]['stage_name'] = attributes.get('stage_name')
    result[domain_name]['base_path'] = attributes.get('base_path')

    result = clean_json_values(value=result)
    return result


def apigateway_base_path_mapping_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes['domain_name']}/{attributes['base_path']}"


def apigateway_base_path_mapping_second_index(attributes, arg=None, additional_data=None):
    return f"{attributes['domain_name']}_"

### CLOUDFRONT ###


def cloudfront_build_origin(attributes, arg=None, additional_data=None):
    # Create a deep copy of the attributes to avoid modifying the original
    attributes_copy = copy.deepcopy(attributes)
    origin_list = attributes_copy.get("origin", [])
    result = {}

    for origin in origin_list:
        origin_key = origin['origin_id']

        # Remove empty fields and convert lists to their first item
        transformed_origin = {}
        for k, v in origin.items():
            if v:  # check if the value is not empty
                if k in ("custom_header"):
                    transformed_origin[k] = v
                elif isinstance(v, list):
                    transformed_origin[k] = v[0]
                else:
                    transformed_origin[k] = v

        result[origin_key] = transformed_origin

    return result


def cloudfront_build_default_cache_behavior(attributes, arg=None, additional_data=None):
    default_cache_behavior = attributes.get("default_cache_behavior", [])
    result = {}
    if not default_cache_behavior:
        return result
    instance_data = get_module_additional_data(
        "aws_cloudfront_distribution", "managed_policies", additional_data)
    for k, v in default_cache_behavior[0].items():
        if v:  # check if the value is not empty
            if k == "cache_policy_id":
                cache_policy_name = instance_data.get(v, "")
                if cache_policy_name:
                    result["cache_policy_name"] = cache_policy_name
                else:
                    result[k] = v
                continue
            if k == "lambda_function_association":
                assoc_result = {}
                for association in v:
                    assoc_key = association['event_type']
                    assoc_result[assoc_key] = {}
                    assoc_result[assoc_key]['lambda_arn'] = association['lambda_arn']
                    assoc_result[assoc_key]['include_body'] = association['include_body']
                result[k] = assoc_result
                continue

            if k == "function_association":
                assoc_result = {}
                for association in v:
                    assoc_key = association['event_type']
                    assoc_result[assoc_key] = {}
                    assoc_result[assoc_key]['function_arn'] = association['function_arn']
                result[k] = assoc_result
                continue

            if k == "forwarded_values":
                for forwarded_value in v:
                    assoc_result = {}
                    assoc_result["headers"] = forwarded_value.get(
                        "headers", [])
                    assoc_result["query_string"] = forwarded_value.get(
                        "query_string", False)
                    assoc_result["cookies_forward"] = forwarded_value.get(
                        "cookies", [{}])[0].get("forward", "none")
                    assoc_result["cookies_whitelisted_names"] = forwarded_value.get(
                        "cookies", [{}])[0].get("whitelisted_names", [])
                    assoc_result["query_string_cache_keys"] = forwarded_value.get(
                        "query_string_cache_keys", [])
                    result[k] = [assoc_result]
                continue

            if isinstance(v, list):
                if isinstance(v[0], dict):
                    result[k] = v[0]
                else:
                    result[k] = v
            else:
                result[k] = v
    return result


def cloudfront_build_ordered_cache_behavior(attributes, arg=None, additional_data=None):
    ordered_cache_behavior = attributes.get("ordered_cache_behavior", [])
    result = []
    if not ordered_cache_behavior:
        return result
    instance_data = get_module_additional_data(
        "aws_cloudfront_distribution", "managed_policies", additional_data)
    for cache_behavior in ordered_cache_behavior:
        record = {}
        for k, v in cache_behavior.items():
            if v:
                if k == "cache_policy_id":
                    cache_policy_name = instance_data.get(v, "")
                    if cache_policy_name:
                        record["cache_policy_name"] = cache_policy_name
                    else:
                        record[k] = v
                    continue
                if k == "lambda_function_association":
                    assoc_result = {}
                    for association in v:
                        assoc_key = association['event_type']
                        assoc_result[assoc_key] = {}
                        assoc_result[assoc_key]['lambda_arn'] = association['lambda_arn']
                        assoc_result[assoc_key]['include_body'] = association['include_body']
                    record[k] = assoc_result
                    continue

                if k == "function_association":
                    assoc_result = {}
                    for association in v:
                        assoc_key = association['event_type']
                        assoc_result[assoc_key] = {}
                        assoc_result[assoc_key]['function_arn'] = association['function_arn']
                    record[k] = assoc_result
                    continue

                if k == "forwarded_values":
                    for forwarded_value in v:
                        assoc_result = {}
                        assoc_result["headers"] = forwarded_value.get(
                            "headers", [])
                        assoc_result["query_string"] = forwarded_value.get(
                            "query_string", False)
                        assoc_result["cookies_forward"] = forwarded_value.get(
                            "cookies", [{}])[0].get("forward", "none")
                        assoc_result["cookies_whitelisted_names"] = forwarded_value.get(
                            "cookies", [{}])[0].get("whitelisted_names", [])
                        assoc_result["query_string_cache_keys"] = forwarded_value.get(
                            "query_string_cache_keys", [])
                        record[k] = [assoc_result]
                    continue

                if isinstance(v, list):
                    if isinstance(v[0], dict):
                        record[k] = v[0]
                    else:
                        record[k] = v
                else:
                    record[k] = v
        result.append(record)
    return result


def cloudfront_build_geo_restriction(attributes, arg=None, additional_data=None):
    restrictions = attributes.get("restrictions", [])
    result = {}
    if not restrictions:
        return result
    if 'geo_restriction' in restrictions[0]:
        if restrictions[0]['geo_restriction'][0].get('restriction_type', 'none') != 'none':
            result = restrictions[0]['geo_restriction'][0]
    return result


def cloudfront_build_viewer_certificate(attributes, arg=None, additional_data=None):
    viewer_certificate = attributes.get("viewer_certificate", [])
    result = {}
    if not viewer_certificate:
        return result
    for k, v in viewer_certificate[0].items():
        if v:  # check if the value is not empty
            if isinstance(v, list):
                if isinstance(v[0], dict):
                    result[k] = v[0]
                else:
                    result[k] = v
            else:
                result[k] = v
    return result


### CLOUDMAP ###
def cloudmap_get_vpc_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_service_discovery_private_dns_namespace", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def cloudmap_build_service_names(attributes, arg=None, additional_data=None):
    key = attributes.get("name")
    result = {}
    result[key] = {
        'name': attributes.get("name"),
        'description': attributes.get("description"),
        'dns_records': attributes.get("dns_config", [{}])[0].get("dns_records", [{}]),
        'routing_policy': attributes.get("dns_config", [{}])[0].get("routing_policy", ""),
        'health_check_config': attributes.get("health_check_config"),
        'health_check_custom_config': attributes.get("health_check_custom_config"),
        'tags': attributes.get("tags"),
    }
    return result


def cloudmap_private_dns_namespace_import_id(attributes, arg=None, additional_data=None):
    namespace_id = attributes.get("id")
    vpc_id = attributes.get("vpc")
    return f"{namespace_id}:{vpc_id}"

### DOCDB ###


def docdb_build_cluster_instances(attributes, arg=None, additional_data=None):
    key = attributes[arg]
    result = {key: {}}
    for k in ['identifier', 'apply_immediately', 'preferred_maintenance_window', 'instance_class', 'engine', 'auto_minor_version_upgrade', 'enable_performance_insights', 'promotion_tier', 'tags']:
        val = attributes.get(k)
        if isinstance(val, str):
            val = val.replace('${', '$${')
        result[key][k] = val
    return result


def docdb_get_subnet_names(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_docdb_subnet_group", id, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    return subnet_names


def docdb_get_subnet_ids(attributes, arg=None, additional_data=None):
    subnet_names = docdb_get_subnet_names(attributes, arg, additional_data)
    if subnet_names:
        return ""
    subnet_ids = attributes.get("subnet_ids")
    return subnet_ids


def docdb_get_vpc_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_docdb_subnet_group", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def docdb_get_vpc_id(attributes, arg=None, additional_data=None):
    vpc_name = docdb_get_vpc_name(attributes, arg, additional_data)
    if vpc_name:
        return ""
    instance_data = get_module_additional_data(
        "aws_docdb_subnet_group", id, additional_data)
    vpc_id = instance_data.get("vpc_id", "")
    return vpc_id


### DYNAMODB ###
def dynamodb_replica_regions(attributes, arg=None, additional_data=None):
    replicas = attributes.get("replica", [])
    result_list = []
    for replica in replicas:
        result = {}
        region_name = replica.get("region_name")
        result['region_name'] = region_name
        kms_key_arn = replica.get("kms_key_arn")
        if kms_key_arn:
            result['kms_key_arn'] = kms_key_arn
        propagate_tags = replica.get("propagate_tags")
        result['propagate_tags'] = propagate_tags
        point_in_time_recovery = replica.get("point_in_time_recovery")
        result['point_in_time_recovery'] = point_in_time_recovery
        result_list.append(result)
    return result_list


def dynamodb_aws_appautoscaling_policy_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes.get('service_namespace')}/{attributes.get('resource_id')}/{attributes.get('scalable_dimension')}/{attributes.get('name')}"


def dynamodb_aws_appautoscaling_target_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes.get('service_namespace')}/{attributes.get('resource_id')}/{attributes.get('scalable_dimension')}"


def dynamodb_get_name_from_arn(attributes, arg=None, additional_data=None):
    arn = attributes.get(arg)
    if arn is not None:
        return arn.split('/')[-1]
    return None


def dynamodb_aws_dynamodb_target_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_dynamodb_table", id, additional_data)
    target_name = instance_data.get("target_name", "")
    return target_name


def dynamodb_build_autoscaling(attributes, arg=None, additional_data=None):
    scalable_dimension = attributes.get("scalable_dimension", "")
    name = get_scalable_dimension(scalable_dimension)

    result = {}
    result[name] = {}
    result[name]["max_capacity"] = attributes.get("max_capacity", None)
    result[name]["min_capacity"] = attributes.get("min_capacity", None)
    result[name]["scalable_dimension"] = scalable_dimension
    result[name]["tags"] = attributes.get("tags", None)
    return result


def get_scalable_dimension(scalable_dimension):
    if scalable_dimension == "dynamodb:table:ReadCapacityUnits":
        name = "table_read_policy"
    elif scalable_dimension == "dynamodb:table:WriteCapacityUnits":
        name = "table_write_policy"
    elif scalable_dimension == "dynamodb:index:ReadCapacityUnits":
        name = "index_read_policy"
    elif scalable_dimension == "dynamodb:index:WriteCapacityUnits":
        name = "index_write_policy"

    return name


def dynamodb_get_autosaling_type(attributes, arg=None, additional_data=None):
    scalable_dimension = attributes.get("scalable_dimension", "")
    return get_scalable_dimension(scalable_dimension)


def dynamodb_build_autoscaling_policy(attributes, arg=None, additional_data=None):
    scalable_dimension = attributes.get("scalable_dimension", "")
    name = get_scalable_dimension(scalable_dimension)
    result = {}
    result[name] = {}
    result[name]["policy_name"] = attributes.get("name", None)
    tmp = attributes.get("target_tracking_scaling_policy_configuration", [])
    if tmp:
        tmp2 = tmp[0].get("predefined_metric_specification", [])
        if tmp2:
            result[name]["predefined_metric_type"] = tmp2[0].get(
                "predefined_metric_type", None)
        result[name]["scale_in_cooldown"] = tmp[0].get(
            "scale_in_cooldown", None)
        result[name]["scale_out_cooldown"] = tmp[0].get(
            "scale_out_cooldown", None)
        result[name]["target_value"] = tmp[0].get("target_value", None)

    return result


### EC2 ###

def get_vpc_name_ec2(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_instance", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def get_vpc_id_ec2(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    vpc_name = get_vpc_name_ec2(attributes, arg, additional_data)
    if not vpc_name:
        instance_data = get_module_additional_data(
            "aws_instance", id, additional_data)
        vpc_id = instance_data.get("vpc_id", "")
        return vpc_id
    else:
        return ""


def ec2_get_root_block_device(attributes, arg=None, additional_data=None):
    root_block_devices = attributes.get("root_block_device", [])
    for root_block_device in root_block_devices:
        kms_key_id = root_block_device.get("kms_key_id")
        if kms_key_id:
            id = attributes.get("id")
            instance_data = get_module_additional_data(
                "aws_instance", id, additional_data)
            kms_key_alias = instance_data.get("kms_key_alias", "")
            if kms_key_alias:
                root_block_device["kms_key_alias"] = kms_key_alias
                del root_block_device["kms_key_id"]
        del root_block_device["device_name"]
        del root_block_device["volume_id"]
        del root_block_device["iops"]

        return clean_json_values(value=root_block_device)
    return {}


def ec2_get_public_ip_addresses(attributes, arg=None, additional_data=None):
    result = {}
    public_ip = attributes.get("public_ip")
    if public_ip is not None:
        tags = attributes.get("tags")
        result[public_ip] = {'tags': tags}
    return result


def ec2_get_user_data(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_instance", id, additional_data)
    user_data = instance_data.get("user_data", "")
    return user_data


def get_subnet_name_ec2(attributes, arg=None, additional_data=None):
    id = attributes.get('id')
    instance_data = get_module_additional_data(
        "aws_instance", id, additional_data)
    subnet_name = instance_data.get("subnet_name", "")
    return subnet_name


def get_subnet_id_ec2(attributes, arg=None, additional_data=None):
    subnet_name = get_subnet_name_ec2(attributes, arg, additional_data)
    if subnet_name:
        return ""
    else:
        return attributes.get("subnet_id")


def ec2_get_device_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_ebs_volume", id, additional_data)
    device_name = instance_data.get("device_name", "")
    return device_name


def ec2_get_device_name_list(attributes, arg=None, additional_data=None):
    volume_id = attributes.get("id")
    device_name = ec2_get_device_name(attributes, arg, additional_data)
    if not device_name:
        return None

    result = {}
    result[device_name] = {}

    volume_type = attributes.get("type")
    iops = attributes.get("iops")
    throughput = attributes.get("throughput")

    if volume_type != "gp2" and iops:
        result[device_name]["iops"] = iops

    if throughput and throughput != 0:
        result[device_name]["throughput"] = throughput

    # Add other fields conditionally if they are not empty or have a non-zero value
    for key in ["size", "tags", "encrypted", "kms_key_id", "type"]:
        value = attributes.get(key)
        if key == "kms_key_id":
            # Get the key alias if it exists using boto3
            if value:
                instance_data = get_module_additional_data(
                    "aws_ebs_volume", volume_id, additional_data)
                kms_alias = instance_data.get("kms_key_alias", "")
                if kms_alias:
                    value = kms_alias
                    key = "kms_key_alias"
        if value:
            result[device_name][key] = value

    return result


def get_kms_key_alias_ec2(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_instance", id, additional_data)
    kms_key_alias = instance_data.get("kms_key_alias", "")
    return kms_key_alias


def get_kms_key_id_ec2(attributes, arg=None, additional_data=None):
    root_block_device = attributes.get("root_block_device")
    if root_block_device:
        kms_key_id = root_block_device[0].get("kms_key_id")
        kms_key_alias = get_kms_key_alias_ec2(attributes, arg, additional_data)
        if not kms_key_alias:
            return kms_key_id
    return None


### ECR ###
def ecr_build_registry_replication_rules(attributes, arg=None, additional_data=None):
    formatted_rules = []
    replication_configuration = attributes.get("replication_configuration", [])
    if not replication_configuration:
        return formatted_rules
    for replication in replication_configuration:
        rules = replication.get("rule", [])
        if not rules:
            continue
        for rule in rules:
            destinations = rule.get("destination", [])
            records = []
            for destination in destinations:
                records.append({
                    "region": destination["region"],
                    "registry_id": destination["registry_id"]
                })
            formatted_rules.append({
                "destinations": records
            })
    return formatted_rules


def ecr_get_registry_scan_rules(attributes, arg=None, additional_data=None):
    result = []
    rules = attributes.get("rule", [])
    for rule in rules:
        record = {}
        record["scan_frequency"] = rule.get("scan_frequency", None)
        repository_filter = rule.get('repository_filter')
        record["repository_filter"] = []
        for filter in repository_filter:
            record2 = {}
            record2["filter"] = filter.get("filter")
            record2["filter_type"] = filter.get("filter_type")
            record["repository_filter"].append(record2)

        result.append(record)
    return result


def ecr_get_repository_kms_key_alias(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_ecr_repository", id, additional_data)
    if not instance_data:
        return ""
    kms_key_alias = instance_data.get("kms_key_alias", "")
    return kms_key_alias


def ecr_get_repository_kms_key(attributes, arg=None, additional_data=None):
    kms_key_alias = ecr_get_repository_kms_key_alias(
        attributes, arg, additional_data)
    if kms_key_alias:
        return ""
    else:
        return attributes.get("kms_key_id")


### ECS ###
def ecs_get_network_field(attributes, arg=None, additional_data=None):
    tmp = attributes.get('network_configuration')
    if tmp:
        network_configuration = attributes['network_configuration'][0]
        if arg in network_configuration:
            return network_configuration[arg]
    return None


def ecs_task_definition_id(attributes, arg=None, additional_data=None):
    # The name is expected to be in the format /aws/ecs/{cluster_name}
    arn = attributes.get('arn')
    if arn is not None:
        # split the string by '/' and take the last part as the cluster_arn
        return arn.split('/')[-1]
    return None


def ecs_autoscaling_policies(attributes, arg=None, additional_data=None):
    name = attributes.get('name')
    result = {name: {}}

    if attributes.get('name'):
        result[name]['name'] = attributes.get('name')
    if attributes.get('policy_type'):
        result[name]['policy_type'] = attributes.get('policy_type')

    if attributes.get('step_scaling_policy_configuration'):
        result[name]['step_scaling_policy_configuration'] = attributes.get(
            'step_scaling_policy_configuration')

    if attributes.get('target_tracking_scaling_policy_configuration'):
        result[name]['target_tracking_scaling_policy_configuration'] = attributes.get(
            'target_tracking_scaling_policy_configuration')[0]
        if result[name]['target_tracking_scaling_policy_configuration']['predefined_metric_specification']:
            result[name]['target_tracking_scaling_policy_configuration']['predefined_metric_specification'] = result[
                name]['target_tracking_scaling_policy_configuration']['predefined_metric_specification'][0]
        else:
            del result[name]['target_tracking_scaling_policy_configuration']['predefined_metric_specification']

        if result[name]['target_tracking_scaling_policy_configuration']['customized_metric_specification']:
            result[name]['target_tracking_scaling_policy_configuration']['customized_metric_specification'] = result[
                name]['target_tracking_scaling_policy_configuration']['customized_metric_specification'][0]
        else:
            del result[name]['target_tracking_scaling_policy_configuration']['customized_metric_specification']

    if attributes.get('scaling_adjustment'):
        result[name]['scaling_adjustment'] = attributes.get(
            'scaling_adjustment')

    return result


def ecs_autoscaling_scheduled_actions(attributes, arg=None, additional_data=None):
    name = attributes.get('name')
    result = {name: {}}

    if attributes.get('name'):
        result[name]['name'] = attributes.get('name')
    if attributes.get('min_capacity'):
        result[name]['min_capacity'] = attributes.get('min_capacity')
    if attributes.get('max_capacity'):
        result[name]['max_capacity'] = attributes.get('max_capacity')
    if attributes.get('schedule'):
        result[name]['schedule'] = attributes.get('schedule')
    if attributes.get('start_time'):
        result[name]['start_time'] = attributes.get('start_time')
    if attributes.get('end_time'):
        result[name]['end_time'] = attributes.get('end_time')
    if attributes.get('timezone'):
        result[name]['timezone'] = attributes.get('timezone')

    return result


def ecs_task_definition_volume(attributes, arg=None, additional_data=None):
    result = {}
    volumes = attributes.get('volume')

    for volume in volumes:
        cleaned_volume = {k: v for k, v in volume.items() if v != []}
        result[cleaned_volume['name']] = cleaned_volume

    return result


def ecs_get_name_from_arn(attributes, arg=None, additional_data=None):
    arn = attributes.get(arg)
    if arn is not None:
        # split the string by '/' and take the last part as the cluster_arn
        return arn.split('/')[-1]
    return None


def ecs_build_service_registries(attributes, arg=None, additional_data=None):
    result = {}
    service_registries = attributes.get(arg, [])
    if service_registries:
        sg = service_registries[0]
        # Reading the ARN
        registry_arn = sg.get('registry_arn')
        instance_data = get_module_additional_data(
            "aws_service_discovery_service", registry_arn, additional_data)
        registry_name = instance_data.get('registry_name')
        namespace_name = instance_data.get('namespace_name')
        # Adding the registry_name, namespace_name, port, container_name, and container_port to the result
        result['registry_name'] = registry_name
        result['namespace_name'] = namespace_name
        result['port'] = sg.get('port')
        result['container_name'] = sg.get('container_name')
        result['container_port'] = sg.get('container_port')

    return result


def ecs_service_import_id(attributes, arg=None, additional_data=None):
    service_arn = attributes.get('id')
    cluster_arn = attributes.get('cluster')
    return cluster_arn.split('/')[-1]+"/"+service_arn.split('/')[-1]


def ecs_task_definition_import_id(attributes, arg=None, additional_data=None):
    return attributes.get('arn')


def ecs_appautoscaling_policy_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes.get('service_namespace')}/{attributes.get('resource_id')}/{attributes.get('scalable_dimension')}/{attributes.get('name')}"


def ecs_appautoscaling_target_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes.get('service_namespace')}/{attributes.get('resource_id')}/{attributes.get('scalable_dimension')}"


def ecs_get_network_configuration(attributes, arg=None, additional_data=None):
    network_configuration = attributes.get(arg, [])
    service_arn = attributes.get('id')
    if network_configuration:
        instance_data = get_module_additional_data(
            "aws_ecs_service", service_arn, additional_data)
        subnet_names = instance_data.get('subnet_names', [])
        if subnet_names:
            network_configuration[0]['subnet_names'] = subnet_names
            del network_configuration[0]['subnets']
    return network_configuration


def get_vpc_name_ecs(attributes, arg=None, additional_data=None):
    service_arn = attributes.get('id')
    instance_data = get_module_additional_data(
        "aws_ecs_service", service_arn, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def get_vpc_id_ecs(attributes, arg=None, additional_data=None):
    vpc_name = get_vpc_name_ecs(attributes, arg, additional_data)
    if not vpc_name:
        return attributes.get("vpc_id")
    else:
        return ""


### EKS ###
def eks_build_cluster_addons(attributes, arg=None, additional_data=None):
    addon_name = attributes.get("addon_name")
    result = {}
    result[addon_name] = {}
    result[addon_name]['name'] = addon_name
    result[addon_name]['addon_version'] = attributes.get("addon_version")
    result[addon_name]['configuration_values'] = attributes.get(
        "configuration_values")
    result[addon_name]['preserve'] = attributes.get("preserve")
    result[addon_name]['resolve_conflicts'] = attributes.get(
        "resolve_conflicts")
    result[addon_name]['service_account_role_arn'] = attributes.get(
        "service_account_role_arn")
    result[addon_name]['tags'] = attributes.get("tags")

    # Remove the keys that are empty
    result[addon_name] = {k: v for k,
                          v in result[addon_name].items() if v is not None}
    return result


def eks_cloudwatch_log_group_name(attributes, arg=None, additional_data=None):
    # The name is expected to be in the format /aws/ecs/{cluster_name}
    name = attributes.get('name')
    if name is not None:
        # split the string by '/' and take the last part as the cluster_name
        parts = name.split('/')
        if len(parts) > 3:
            return parts[3]  # return 'cluster_name'
    # In case the name doesn't match the expected format, return None or you could return some default value
    return None


def eks_build_cluster_tags(attributes, arg=None, additional_data=None):
    key = attributes.get("key")
    value = attributes.get("value")
    return {key: value}


def eks_join_ec2_tag_resource_id(parent_attributes, child_attributes):
    vpc_config = parent_attributes.get("vpc_config")
    if vpc_config:
        cluster_security_group_id = vpc_config[0].get(
            "cluster_security_group_id")
    resource_id = child_attributes.get("resource_id")
    if cluster_security_group_id == resource_id:
        return True
    return False


def join_eks_cluster_and_oidc_provider(parent_attributes, child_attributes):
    # Extract the expected OIDC issuer URL from the EKS cluster's attributes
    identity = parent_attributes.get("identity", [])
    if len(identity) == 0:
        return False

    expected_oidc_url = identity[0].get("oidc", [{}])[0].get("issuer", "")

    # Extract the URL for the OIDC provider from its attributes
    provider_url = child_attributes.get("url", "")

    # Check if the OIDC provider URL matches the one from the EKS cluster
    return provider_url == expected_oidc_url.replace("https://", "")


def eks_join_node_group_autoscaling_schedule(parent_attributes, child_attributes):
    # Assuming parent_attributes contains a list of associated ASG names for the EKS node group.
    node_asg_names = parent_attributes.get("resources", {}).get(
        "autoScalingGroups", [{}])[0].get("name", "")

    # Assuming child_attributes contains the name of the ASG the schedule applies to.
    schedule_asg_name = child_attributes.get("autoscaling_group_name", "")

    return node_asg_names == schedule_asg_name


def get_node_group_name(attributes, arg=None, additional_data=None):
    node_group_name_prefix = attributes.get("node_group_name_prefix")
    node_group_name = ""
    if node_group_name_prefix:
        if "-" in node_group_name_prefix:
            node_group_name = node_group_name_prefix.rsplit("-", 1)[0]
        else:
            node_group_name = node_group_name_prefix
    else:
        node_group_name = attributes.get("node_group_name")
    return node_group_name


def eks_build_managed_node_groups(attributes, arg=None, additional_data=None):
    use_name_prefix = False
    node_group_name_prefix = attributes.get("node_group_name_prefix")
    node_group_name = ""
    if node_group_name_prefix:
        use_name_prefix = True
        if "-" in node_group_name_prefix:
            node_group_name = node_group_name_prefix.rsplit("-", 1)[0]
        else:
            node_group_name = node_group_name_prefix
    else:
        node_group_name = attributes.get("node_group_name")

    result = {node_group_name: {}}
    result[node_group_name]['use_name_prefix'] = use_name_prefix

    subnet_ids = attributes.get(
        "subnet_ids")

    cluster_name = attributes.get("cluster_name")
    instance_data = get_module_additional_data(
        "aws_eks_node_group", cluster_name + ":" + node_group_name, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    if subnet_names:
        result[node_group_name]['subnet_names'] = subnet_names
    else:
        result[node_group_name]['subnet_ids'] = subnet_ids

    scaling_config = attributes.get("scaling_config")
    if scaling_config:
        result[node_group_name]['min_size'] = scaling_config[0].get("min_size")
        result[node_group_name]['max_size'] = scaling_config[0].get("max_size")
        result[node_group_name]['desired_size'] = scaling_config[0].get(
            "desired_size")
    result[node_group_name]['ami_type'] = attributes.get("ami_type")
    result[node_group_name]['ami_release_version'] = attributes.get(
        "ami_release_version")
    result[node_group_name]['capacity_type'] = attributes.get(
        "capacity_type")
    result[node_group_name]['disk_size'] = attributes.get("disk_size")
    result[node_group_name]['force_update_version'] = attributes.get(
        "force_update_version")
    result[node_group_name]['instance_types'] = attributes.get(
        "instance_types")
    result[node_group_name]['labels'] = attributes.get("labels")
    tmp = attributes.get("remote_access")
    if tmp:
        result[node_group_name]['remote_access'] = attributes.get(
            "remote_access")[0]
    result[node_group_name]['taints'] = attributes.get("taint")
    result[node_group_name]['iam_role_arn'] = attributes.get("node_role_arn")

    if attributes.get("tags", {}) != {}:
        result[node_group_name]['tags'] = attributes.get("tags")
    tmp = attributes.get("update_config")
    if tmp:
        result[node_group_name]['update_config'] = attributes.get(
            "update_config")[0]
        # Remove the keys that are empty or 0
        result[node_group_name]['update_config'] = {k: v for k,
                                                    v in result[node_group_name]['update_config'].items() if v is not None and v != 0}
    result[node_group_name]['timeouts'] = attributes.get("timeouts")

    # Remove the keys that are empty
    result[node_group_name] = {k: v for k,
                               v in result[node_group_name].items() if v is not None}
    # Get launch_template_version
    launch_template = attributes.get("launch_template")
    if launch_template:
        launch_template_version = launch_template[0].get("version")
        result[node_group_name]["launch_template_version"] = launch_template_version
        launch_template_id = launch_template[0].get("id")
        result[node_group_name]["launch_template_id"] = launch_template_id

    return result


def eks_asg_get_node_group_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_autoscaling_schedule", id, additional_data)
    node_group_name = instance_data.get("node_group_name", "")
    return node_group_name


def eks_build_node_group_autoscaling_schedules(attributes, arg=None, additional_data=None):
    node_group_name = eks_asg_get_node_group_name(
        attributes, arg, additional_data)
    result = {}
    result[node_group_name] = {}
    result[node_group_name]['schedules'] = {}
    result[node_group_name]['schedules']["min_size"] = attributes.get(
        "min_size")
    result[node_group_name]['schedules']["max_size"] = attributes.get(
        "max_size")
    result[node_group_name]['schedules']["desired_capacity"] = attributes.get(
        "desired_capacity")
    result[node_group_name]['schedules']["start_time"] = attributes.get(
        "start_time")
    result[node_group_name]['schedules']["end_time"] = attributes.get(
        "end_time")
    result[node_group_name]['schedules']["time_zone"] = attributes.get(
        "time_zone")

    # Remove the keys that are empty
    result[node_group_name]['schedules'] = {k: v for k,
                                            v in result[node_group_name]['schedules'].items() if v is not None}
    return result


def eks_get_subnet_names(attributes, arg=None, additional_data=None):
    id = attributes.get("id")

    # print("=================", id, additional_data)
    instance_data = get_module_additional_data(
        "aws_eks_cluster", id, additional_data)
    # print("instance_data", instance_data)
    subnet_names = instance_data.get("subnet_names", [])
    # print("subnet_names", subnet_names)
    return subnet_names


def eks_get_subnet_ids(attributes, arg=None, additional_data=None):
    subnet_names = eks_get_subnet_names(attributes, arg, additional_data)
    if subnet_names:
        return ""
    else:
        return get_field_from_attrs(attributes, 'vpc_config.subnet_ids')


def get_vpc_name_eks(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_eks_cluster", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def get_vpc_id_eks(attributes, arg=None, additional_data=None):
    vpc_name = get_vpc_name_eks(attributes, arg, additional_data)
    if not vpc_name:
        return get_field_from_attrs(
            attributes, 'vpc_config.vpc_id')
    else:
        return ""

### ELASTICCACHE REDIS ###


def ec_redis_get_subnet_names(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_elasticache_subnet_group", id, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    return subnet_names


def ec_redis_get_subnet_ids(attributes, arg=None, additional_data=None):
    subnet_names = ec_redis_get_subnet_names(attributes, arg, additional_data)
    if subnet_names:
        return ""
    else:
        return attributes.get("subnet_ids")


def ec_redis_get_vpc_name_by_subnet(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_elasticache_subnet_group", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def ec_redis_get_vpc_id_by_subnet(attributes, arg=None, additional_data=None):
    vpc_name = ec_redis_get_vpc_name_by_subnet(
        attributes, arg, additional_data)
    if not vpc_name:
        return attributes.get(arg)
    else:
        return ""


def ec_redis_get_vpc_name_by_group(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    subnet_group_name = attributes.get("subnet_group_name")
    instance_data = get_module_additional_data(
        "aws_elasticache_replication_group", subnet_group_name, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def ec_redis_get_vpc_id_by_group(attributes, arg=None, additional_data=None):
    vpc_name = ec_redis_get_vpc_name_by_group(attributes, arg, additional_data)
    vpc_id = ""
    if not vpc_name:
        id = attributes.get("id")
        subnet_group_name = attributes.get("subnet_group_name")
        instance_data = get_module_additional_data(
            "aws_elasticache_replication_group", subnet_group_name, additional_data)
        vpc_id = instance_data.get("vpc_id", "")
    return vpc_id


def ec_redis_get_security_group_ids(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_elasticache_replication_group", id, additional_data)
    security_group_ids = instance_data.get("security_group_ids", [])
    return security_group_ids

### LAMBDA ###


# def lambda_get_role_name(attributes, arg=None, additional_data=None):
#     role_arn = attributes.get(arg)
#     role_name = role_arn.split('/')[-1]  # Extract role name from ARN
#     return role_name


def lambda_cloudwatch_log_group_name(attributes, arg=None, additional_data=None):
    # The name is expected to be in the format /aws/ecs/{cluster_name}
    name = attributes.get('name')
    if name is not None:
        # split the string by '/' and take the last part as the cluster_name
        parts = name.split('/')
        if len(parts) > 2:
            return parts[-1]  # return 'cluster_name'
    # In case the name doesn't match the expected format, return None or you could return some default value
    return None


def lambda_vpc_config(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_lambda_function", id, additional_data)
    result = []
    vpc_configs = attributes.get("vpc_config")
    for vpc_config in vpc_configs:
        record = {}
        vpc_name = instance_data.get("vpc_name", "")
        if vpc_name:
            record["vpc_name"] = vpc_name
        else:
            record["vpc_id"] = vpc_config.get("vpc_id")
        subnet_names = instance_data.get("subnet_names", [])
        if subnet_names:
            record["subnet_names"] = subnet_names
        else:
            record["subnet_ids"] = vpc_config.get("subnet_ids")
        record["ipv6_allowed_for_dual_stack"] = vpc_config.get(
            "ipv6_allowed_for_dual_stack")
        record["security_group_ids"] = instance_data.get(
            "security_group_ids", [])
        result.append(record)
    return result

### MSK ###


def msk_get_provisioned_throughput(attributes, arg=None, additional_data=None):
    record = {}
    tmp0 = attributes.get("broker_node_group_info", [])
    if tmp0:
        tmp = tmp0[0].get("storage_info", [])
        if tmp:
            tmp2 = tmp[0].get("ebs_storage_info", [])
            if tmp2:
                tmp3 = tmp2[0].get("provisioned_throughput", [])
                if tmp3:
                    record["enabled"] = tmp3[0].get("enabled")
                    tmp4 = tmp3[0].get("volume_throughput", 0)
                    if tmp4 > 0:
                        record["volume_throughput"] = tmp4
    if record:
        return [record]
    return None


def msk_get_server_properties(attributes, arg=None, additional_data=None):
    server_properties_str = attributes.get(arg)

    if not server_properties_str:
        return None

    properties = {}
    lines = server_properties_str.split("\n")
    for line in lines:
        line = line.strip()  # Removing leading and trailing spaces
        if "=" in line:
            # Split only on the first equals sign
            key, value = line.split("=", 1)
            properties[key.strip()] = value.strip()

    return properties


def msk_get_subnet_names(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_msk_cluster", id, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    return subnet_names


def msk_get_subnet_ids(attributes, arg=None, additional_data=None):
    subnet_names = msk_get_subnet_names(attributes, arg, additional_data)
    if subnet_names:
        return ""
    else:
        return get_field_from_attrs(attributes, 'broker_node_group_info.client_subnets')


def get_vpc_name_msk(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_msk_cluster", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def get_vpc_id_msk(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    vpc_name = get_vpc_name_msk(attributes, arg, additional_data)
    if not vpc_name:
        instance_data = get_module_additional_data(
            "aws_msk_cluster", id, additional_data)
        vpc_id = instance_data.get("vpc_id", "")
        return vpc_id
    else:
        return ""


def msk_join_configuration(parent_attributes, child_attributes):
    configuration_arn = child_attributes.get('arn')
    cluster_configuration = get_field_from_attrs(
        parent_attributes, 'configuration_info.arn')
    if configuration_arn == cluster_configuration:
        return True
    return False


def msk_get_public_access_enabled(attributes, arg, additional_data=None):
    public_access_type = get_field_from_attrs(attributes, arg)
    if public_access_type == "SERVICE_PROVIDED_EIPS":
        return True
    return False


def msk_get_autoscaling_target_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes.get('service_namespace')}/{attributes.get('resource_id')}/{attributes.get('scalable_dimension')}"


def msk_get_autoscaling_policy_import_id(attributes, arg=None, additional_data=None):
    return f"{attributes.get('service_namespace')}/{attributes.get('resource_id')}/{attributes.get('scalable_dimension')}/{attributes.get('name')}"

### RDS ###


def rds_get_db_name(attributes, arg=None, additional_data=None):
    replicate_source_db = attributes.get("replicate_source_db", None)
    if replicate_source_db:
        return None
    return attributes.get("db_name", None)


def rds_get_username(attributes, arg=None, additional_data=None):
    replicate_source_db = attributes.get("replicate_source_db", None)
    if replicate_source_db:
        return None
    return attributes.get("username", None)


def rds_get_subnet_names(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_db_subnet_group", id, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    return subnet_names


def rds_get_subnet_ids(attributes, arg=None, additional_data=None):
    subnet_names = rds_get_subnet_names(attributes, arg, additional_data)
    if subnet_names:
        return ""
    else:
        return attributes.get("subnet_ids")


def rds_get_vpc_name_by_subnet(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_db_subnet_group", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def rds_get_vpc_id_by_subnet(attributes, arg=None, additional_data=None):
    vpc_name = rds_get_vpc_name_by_subnet(
        attributes, arg, additional_data)
    if not vpc_name:
        return attributes.get(arg)
    else:
        return ""


def rds_get_vpc_name_by_group(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    db_subnet_group_name = attributes.get("db_subnet_group_name")
    instance_data = get_module_additional_data(
        "aws_db_instance", db_subnet_group_name, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def rds_get_vpc_id_by_group(attributes, arg=None, additional_data=None):
    vpc_name = rds_get_vpc_name_by_group(attributes, arg, additional_data)
    vpc_id = ""
    if not vpc_name:
        db_subnet_group_name = attributes.get("db_subnet_group_name")
        instance_data = get_module_additional_data(
            "aws_db_instance", db_subnet_group_name, additional_data)
        vpc_id = instance_data.get("vpc_id", "")
    return vpc_id


def rds_get_security_group_ids(attributes, arg=None, additional_data=None):
    identifier = attributes.get("identifier")
    instance_data = get_module_additional_data(
        "aws_db_instance", identifier, additional_data)
    vpc_security_group_ids = instance_data.get("vpc_security_group_ids", [])
    return vpc_security_group_ids


def rds_get_kms_key_alias_backups(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_db_instance_automated_backups_replication", id, additional_data)
    kms_key_alias = instance_data.get("kms_key_alias", "")
    return kms_key_alias


def rds_get_kms_key_id_backups(attributes, arg=None, additional_data=None):
    kms_key_id = attributes.get("kms_key_id")
    kms_key_alias = rds_get_kms_key_alias_backups(
        attributes, arg, additional_data)
    if not kms_key_alias:
        return kms_key_id
    return None


def rds_get_kms_key_alias(attributes, arg=None, additional_data=None):
    identifier = attributes.get("identifier")
    instance_data = get_module_additional_data(
        "aws_db_instance", identifier, additional_data)
    kms_key_alias = instance_data.get("kms_key_alias", "")
    return kms_key_alias


def rds_get_kms_key_id(attributes, arg=None, additional_data=None):
    kms_key_id = attributes.get("kms_key_id")
    kms_key_alias = rds_get_kms_key_alias(
        attributes, arg, additional_data)
    if not kms_key_alias:
        return kms_key_id
    return None


def rds_get_kms_key_alias_performance_insights(attributes, arg=None, additional_data=None):
    identifier = attributes.get("identifier")
    instance_data = get_module_additional_data(
        "aws_db_instance", identifier, additional_data)
    kms_key_alias = instance_data.get("performance_insights_kms_key_alias", "")
    return kms_key_alias


def rds_get_kms_key_id_performance_insights(attributes, arg=None, additional_data=None):
    performance_insights_kms_key_id = attributes.get(
        "performance_insights_kms_key_id")
    kms_key_alias = rds_get_kms_key_alias_performance_insights(
        attributes, arg, additional_data)
    if not kms_key_alias:
        return performance_insights_kms_key_id
    return None


def rds_get_final_snapshot_identifier(attributes, arg=None, additional_data=None):
    final_snapshot_identifier = attributes.get("final_snapshot_identifier")
    if final_snapshot_identifier:
        return final_snapshot_identifier
    return None

### S3 ###


def aws_s3_build_logging(state, arg=None, additional_data=None):
    result = {}

    result['target_bucket'] = state.get('target_bucket', '')
    result['target_prefix'] = state.get('target_prefix', '')

    tmp = state.get('target_object_key_format', [])
    if tmp:
        result['target_object_key_format'] = tmp

    return result


def s3_build_tiering(state, arg=None, additional_data=None):
    result = {}
    name = state.get("name", "")
    result[name] = {}
    tiering = state.get("tiering", [])
    if tiering:
        result[name]["tiering"] = tiering
    filter = state.get("filter", [])
    if filter:
        result[name]["filter"] = filter
    status = state.get("status", "")
    if status:
        result[name]["status"] = status
    return result


def aws_s3_get_inventory_configuration(state, arg=None, additional_data=None):
    name = state.get("name", "")
    result = {}
    result[name] = {}
    result[name]["included_object_versions"] = state.get(
        "included_object_versions", "")
    result[name]["enabled"] = state.get("enabled", [])
    result[name]["optional_fields"] = state.get("optional_fields", [])
    tmp = state.get("destination", [])
    if tmp:
        result[name]["destination"] = {}
        tmp2 = tmp[0].get("bucket", [])
        if tmp2:
            result[name]["destination"]["bucket_arn"] = tmp2[0].get(
                "bucket_arn", "")
            result[name]["destination"]["format"] = tmp2[0].get("format", "")
            result[name]["destination"]["account_id"] = tmp2[0].get(
                "account_id", "")
            result[name]["destination"]["prefix"] = tmp2[0].get("prefix", "")
            tmp3 = tmp2[0].get("encryption", [])
            if tmp3:
                result[name]["destination"]["encryption"] = tmp3

    tmp = state.get("schedule", [])
    if tmp:
        result[name]["frequency"] = tmp[0].get("frequency", "")
    result[name]["filter"] = state.get("filter", [])
    return result


def aws_s3_get_analytics_configuration(state, arg=None, additional_data=None):
    name = state.get("name", "")
    result = {}
    result[name] = {}
    result[name]["filter"] = state.get("filter", [])

    tmp = state.get("storage_class_analysis", [])
    if tmp:
        result[name]["storage_class_analysis"] = {}
        tmp2 = tmp[0].get("data_export", [])
        if tmp2:
            result[name]["storage_class_analysis"]["output_schema_version"] = tmp2[0].get(
                "output_schema_version", "")
            tmp3 = tmp2[0].get("destination", [])
            if tmp3:
                tmp4 = tmp3[0].get("s3_bucket_destination", [])
                if tmp4:
                    result[name]["storage_class_analysis"]["destination_bucket_arn"] = tmp4[0].get(
                        "bucket_arn", "")
                    result[name]["storage_class_analysis"]["export_format"] = tmp4[0].get(
                        "format", "")
                    result[name]["storage_class_analysis"]["destination_account_id"] = tmp4[0].get(
                        "bucket_account_id", "")
                    result[name]["storage_class_analysis"]["export_prefix"] = tmp4[0].get(
                        "prefix", "")
    return result


def aws_s3_build_replication_configuration(state, arg=None, additional_data=None):
    result = {}
    result["role"] = state.get("role", "")

    result["rule"] = []
    rules = state.get("rule")
    for rule in rules:
        record = {}
        tmp = rule.get("id", "")
        if tmp:
            record["id"] = tmp
        tmp = rule.get("prefix", "")
        if tmp:
            record["prefix"] = tmp
        tmp = rule.get("priority", "")
        if tmp:
            record["priority"] = tmp
        tmp = rule.get("status", "")
        if tmp:
            record["status"] = tmp
        # delete_marker_replication_status
        tmp = rule.get("delete_marker_replication")
        if tmp:
            record["delete_marker_replication"] = tmp[0].get(
                "status", "")
        # existing_object_replication_status
        tmp = rule.get("existing_object_replication")
        if tmp:
            record["existing_object_replication"] = tmp[0].get(
                "status", "")
        # destination
        tmp = rule.get("destination")
        if tmp:
            record["destination"] = {}
            tmp2 = tmp[0].get("bucket", "")
            if tmp2:
                record["destination"]["bucket"] = tmp2
            tmp2 = tmp[0].get("storage_class", "")
            if tmp2:
                record["destination"]["storage_class"] = tmp2
            record["destination"]["account"] = tmp[0].get("account")
            # access_control_translation
            tmp2 = tmp[0].get("access_control_translation")
            if tmp2:
                record["destination"]["access_control_translation"] = {}
                record["destination"]["access_control_translation"]["owner"] = tmp2[0].get(
                    "owner", "")
            # encryption_configuration
            tmp2 = tmp[0].get("encryption_configuration")
            if tmp2:
                record["destination"]["encryption_configuration"] = {}
                record["destination"]["encryption_configuration"]["replica_kms_key_id"] = tmp2[0].get(
                    "replica_kms_key_id", "")

            # replication_time
            tmp2 = tmp[0].get("replication_time")
            if tmp2:
                record["destination"]["replication_time"] = {}
                record["destination"]["replication_time"]["status"] = tmp2[0].get(
                    "status", "")
                tmp3 = tmp2[0].get("time", [])
                if tmp3:
                    record["destination"]["replication_time"]["minutes"] = tmp3[0].get(
                        "minutes", [])
            # metrics
            tmp2 = tmp[0].get("metrics")
            if tmp2:
                record["destination"]["metrics"] = {}
                record["destination"]["metrics"]["status"] = tmp2[0].get(
                    "status", "")
                tmp3 = tmp2[0].get("event_threshold", [])
                if tmp3:
                    record["destination"]["metrics"]["minutes"] = tmp3[0].get(
                        "minutes", [])

        # source_selection_criteria
        tmp = rule.get("source_selection_criteria")
        if tmp:
            record["source_selection_criteria"] = {}
            # replica_modifications
            tmp2 = tmp[0].get("replica_modifications")
            if tmp2:
                record["source_selection_criteria"]["replica_modifications"] = {}
                record["source_selection_criteria"]["replica_modifications"]["status"] = tmp2[0].get(
                    "status", "")
            # sse_kms_encrypted_objects
            tmp2 = tmp[0].get("sse_kms_encrypted_objects")
            if tmp2:
                record["source_selection_criteria"]["sse_kms_encrypted_objects"] = {}
                record["source_selection_criteria"]["sse_kms_encrypted_objects"]["status"] = tmp2[0].get(
                    "status", "")
            # tag_filters
            tmp2 = tmp[0].get("tag_filters")
            if tmp2:
                record["source_selection_criteria"]["tag_filters"] = {}
                record["source_selection_criteria"]["tag_filters"]["and"] = tmp2[0].get("and", [
                ])
                record["source_selection_criteria"]["tag_filters"]["prefix"] = tmp2[0].get(
                    "prefix", "")
                record["source_selection_criteria"]["tag_filters"]["tag"] = tmp2[0].get("tag", [
                ])
                record["source_selection_criteria"]["tag_filters"]["not_tag"] = tmp2[0].get(
                    "not_tag", [])
                record["source_selection_criteria"]["tag_filters"]["delimiter"] = tmp2[0].get(
                    "delimiter", "")

        # filter
        tmp = rule.get("filter")
        if tmp:
            record["filter"] = {}
            tmp2 = tmp[0].get("prefix", "")
            if tmp2:
                record["filter"]["prefix"] = tmp2
            tmp2 = tmp[0].get("tag", [])
            if tmp2:
                record["filter"]["tag"] = tmp2
            tmp2 = tmp[0].get("and", [])
            if tmp2:
                record["filter"]["and"] = tmp2
            tmp2 = tmp[0].get("not_tag", [])
            if tmp2:
                record["filter"]["not_tag"] = tmp2
            tmp2 = tmp[0].get("delimiter", "")
            if tmp2:
                record["filter"]["delimiter"] = tmp2
            if not record["filter"]:
                del record["filter"]
        record = clean_json_values(value=record)
        result["rule"].append(record)

    return result


def aws_s3_get_object_lock_configuration_rule(state, arg=None, additional_data=None):
    rule = state.get('rule', [])
    if rule:
        default_retention = rule[0].get('default_retention', [])
        if default_retention:
            rule[0]['default_retention'] = default_retention[0]

    return rule


def aws_s3_bucket_acl_owner(state, arg=None, additional_data=None):
    result = {}

    for item in state['access_control_policy']:
        result = item.get('owner', [{}])[0]
        if 'id' in result:
            del result['id']

    return result


def aws_s3_bucket_acl_grant(state, arg=None, additional_data=None):
    result = []

    current_owner = {}

    for item in state['access_control_policy']:
        current_owner = item.get('owner', [{}])[0]

    for item in state['access_control_policy']:
        grant = item.get('grant', [{}])[0]
        grantee = grant.get('grantee', [{}])[0]
        permission = grant.get('permission', '')

        grantee['permission'] = permission
        if grantee.get('id', '') == current_owner.get('id', ''):
            grantee['type'] = 'CanonicalUser'
            del grantee['id']

        result.append(grantee)

    return result


def aws_s3_bucket_website_configuration_website(state, arg=None, additional_data=None):
    result = {}

    tmp = state.get('index_document')
    if tmp:
        tmp2 = tmp[0].get('suffix', '')
        result['index_document'] = tmp2

    tmp = state.get('error_document')
    if tmp:
        tmp2 = tmp[0].get('key', '')
        result['error_document'] = tmp2

    tmp = state.get('redirect_all_requests_to')
    if tmp:
        result['redirect_all_requests_to'] = tmp[0]

    tmp = state.get('routing_rule')
    if tmp:
        result['routing_rules'] = tmp

    return result


def aws_s3_bucket_ownership_controls_object_ownership(state, arg=None, additional_data=None):
    return state.get('rule', [{}])[0].get('object_ownership', '')


def aws_s3_filter_empty_fields(input_data):
    if isinstance(input_data, dict):
        # Create a new dictionary by recursively calling aws_s3_filter_empty_fields and excluding
        # keys with values that are None, empty strings, empty lists, or empty dicts
        filtered_dict = {k: aws_s3_filter_empty_fields(
            v) for k, v in input_data.items() if v not in [None, '', [], {}]}
        # Further filter out any keys that have None as their values after recursive filtering
        filtered_dict = {k: v for k,
                         v in filtered_dict.items() if v is not None}
        return filtered_dict if filtered_dict else None
    elif isinstance(input_data, list):
        # Filter each element, excluding None, empty strings, empty lists, and empty dicts
        filtered_list = [aws_s3_filter_empty_fields(
            elem) for elem in input_data if elem not in [None, '', [], {}]]
        # Remove any None values that might have been introduced by filtering nested structures
        filtered_list = [elem for elem in filtered_list if elem is not None]
        return filtered_list if filtered_list else None
    else:
        return input_data


def aws_s3_bucket_lifecycle_configuration_lifecycle_rule(state, arg=None, additional_data=None):
    rules = state["rule"]

    result = []
    # i = 0
    for rule in rules:
        transformed_rule = aws_s3_filter_empty_fields(rule)
        for filter in transformed_rule.get('filter', []):
            if 'and' in filter:
                object_size_less_than = filter['and'][0].get(
                    'object_size_less_than', 0)
                if object_size_less_than == 0:
                    del filter['and'][0]['object_size_less_than']
        result.append(transformed_rule)

    return result


def aws_s3_bucket_versioning_versioning(state, arg=None, additional_data=None):
    result = {}

    tmp = state.get('mfa', '')
    if tmp:
        result['mfa'] = tmp

    tmp = state.get('error_document', [{}])[0].get(
        'key', '') if state.get('error_document', [{}]) else ''
    if tmp:
        result['error_document'] = tmp

    tmp = state.get('versioning_configuration', [{}])[0].get(
        'mfa_delete', '')
    if tmp:
        result['mfa_delete'] = tmp

    tmp = state.get('versioning_configuration', [{}])[0].get(
        'status', '')
    if tmp:
        result['status'] = tmp

    return result


def aws_s3_convert_dict_structure(input_dict):
    if isinstance(input_dict, dict):
        for key, value in input_dict.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                input_dict[key] = value[0]
                aws_s3_convert_dict_structure(input_dict[key])
    return input_dict


def aws_s3_server_side_encryption_configuration(state, arg=None, additional_data=None):
    result = {}

    tmp = state.get('rule', '')
    if tmp:
        result['rule'] = tmp

    return aws_s3_convert_dict_structure(result)


def aws_s3_bucket_policy_policy(state, arg=None, additional_data=None):
    # convert the string to a dict
    input_string = state.get(arg, '{}')
    json_dict = json.loads(input_string)

    # convert the dict back to a string, pretty printed
    pretty_json = json.dumps(json_dict, indent=4)

    if pretty_json == '{}':
        return None

    # create the final string with the 'EOF' tags
    result = pretty_json

    return result


### SNS ###
def sns_build_subscriptions(attributes, arg=None, additional_data=None):
    key = attributes['arn'].split(':')[-1]
    result = {key: {}}
    for k, v in attributes.items():
        if v:
            result[key][k] = v
    return result


def sns_get_key_from_arn(attributes, arg=None, additional_data=None):
    key = attributes['arn'].split(':')[-1]
    return key


def sns_signature_version(attributes, arg=None, additional_data=None):
    signature_version = attributes.get("signature_version", None)
    if signature_version != 0:
        return signature_version
    return None

### SQS ###


def sqs_queue_target_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_sqs_queue", id, additional_data)
    is_dlq = instance_data.get("is_dlq", False)
    if is_dlq:
        return "dlq"
    return "this"


def sqs_is_dql(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_sqs_queue", id, additional_data)
    is_dlq = instance_data.get("is_dlq", False)
    return is_dlq


def sqs_get_parent_url(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_sqs_queue", id, additional_data)
    parent_url = instance_data.get("parent_url", "")
    return parent_url

### ELASTICSEARCH ###


def es_get_tags(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_elasticsearch_domain", id, additional_data)
    tags = instance_data.get("tags", [])
    return tags


def es_get_vpc_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_elasticsearch_domain", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def es_get_vpc_options(attributes, arg=None, additional_data=None):
    vpc_options = attributes.get("vpc_options", None)
    if not vpc_options:
        return None
    result = {}
    result["security_group_ids"] = vpc_options[0].get(
        "security_group_ids", None)
    subnet_ids = result["subnet_ids"] = vpc_options[0].get("subnet_ids", None)
    instance_data = get_module_additional_data(
        "aws_elasticsearch_domain", id, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    if subnet_names:
        result["subnet_names"] = subnet_names
        del result["subnet_ids"]
    return result


def es_get_encrypt_at_rest(attributes, arg=None, additional_data=None):
    encrypt_at_rest = attributes.get("encrypt_at_rest", None)
    if encrypt_at_rest:
        kms_key_id = encrypt_at_rest[0].get("kms_key_id", None)
        instance_data = get_module_additional_data(
            "aws_elasticsearch_domain", id, additional_data)

        kms_key_alias = instance_data.get("kms_key_alias", None)
        if kms_key_alias:
            encrypt_at_rest[0]['kms_key_alias'] = kms_key_alias
            del encrypt_at_rest[0]['kms_key_id']
    return encrypt_at_rest


### WAFV2 ###
def wafv2_get_rules(attributes, arg=None, additional_data=None):
    rules = attributes.get("rule", [])
    return rules


def wafv2_web_acl_import_id(attributes, arg=None, additional_data=None):
    id = attributes.get('id')
    name = attributes.get('name')
    scope = attributes.get('scope')
    return f"{id}/{name}/{scope}"


### VPC Endpoint ###
def get_subnet_names_vpce(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_vpc_endpoint", id, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    return subnet_names


def get_subnet_ids_vpce(attributes, arg=None, additional_data=None):
    subnet_names = get_subnet_names_vpce(attributes, arg, additional_data)
    if subnet_names:
        return ""
    else:
        return attributes.get("subnet_ids", [])


def get_vpc_name_vpce(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_vpc_endpoint", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def get_vpc_id_vpce(attributes, arg=None, additional_data=None):
    vpc_name = get_vpc_name_vpce(attributes, arg, additional_data)
    if not vpc_name:
        return attributes.get("vpc_id")
    else:
        return ""


### TARGET GROUP ###
def tg_join_aws_lb_target_group_to_aws_lb_listener_rule(parent_attributes, child_attributes):
    target_group_arn = parent_attributes.get('arn')
    for action in child_attributes.get('action', []):
        if action.get('target_group_arn') == target_group_arn:
            return True
    return False


def tg_get_id_from_arn(attributes, arg=None, additional_data=None):
    arn = attributes.get(arg)
    return arn.split('/')[-1]


def tg_get_listener_rules(attributes, arg=None, additional_data=None):
    result = {}
    key = attributes.get('arn').split('/')[-1]
    result[key] = {}
    result[key]['priority'] = attributes.get('priority')
    result[key]['conditions'] = attributes.get('condition')
    result[key]['tags'] = attributes.get('tags')
    result[key]['listener_arn'] = attributes.get('listener_arn')
    actions = attributes.get('action')
    for action in actions:
        forward = action.get('forward')
        if forward:
            stickiness = forward[0].get('stickiness')
            if stickiness:
                if stickiness[0].get('duration') == 0:
                    del action['forward'][0]['stickiness']
            del action['target_group_arn']

    result[key]['action'] = actions
    return result


def get_vpc_name_tg(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_lb_target_group", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def get_vpc_id_tg(attributes, arg=None, additional_data=None):
    vpc_name = get_vpc_name_tg(attributes, arg, additional_data)
    if not vpc_name:
        return attributes.get("vpc_id")
    else:
        return ""

### AUTOSCALING ###


def asg_get_user_data_configuration(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_launch_configuration", id, additional_data)
    user_data = instance_data.get("user_data", "")
    return user_data


def asg_get_user_data_template(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_launch_template", id, additional_data)
    user_data = instance_data.get("user_data", "")
    return user_data


def asg_build_autoscaling_policies(attributes, arg=None, additional_data=None):
    result = {}
    name = attributes.get("name")
    if not name:
        return result

    policy_details = {}
    attribute_keys = ["policy_type", "scaling_adjustment",
                      "adjustment_type", "cooldown", "enabled"]

    for key in attribute_keys:
        value = attributes.get(key)
        if value or value == 0:
            policy_details[key] = value

    if not policy_details:
        return result

    result[name] = policy_details

    return result


def asg_build_aws_cloudwatch_metric_alarms(attributes, arg=None, additional_data=None):
    result = {}
    alarm_name = attributes.get("alarm_name")
    if not alarm_name:
        return result

    alarm_details = {}

    attribute_keys = ["comparison_operator", "evaluation_periods", "metric_name", "namespace", "period", "statistic", "extended_statistic",
                      "threshold", "treat_missing_data", "ok_actions", "insufficient_data_actions", "dimensions", "alarm_description", "alarm_actions", "tags"]

    for key in attribute_keys:
        value = attributes.get(key)
        if value or value == 0:
            alarm_details[key] = value

    if not alarm_details:
        return result

    result[alarm_name] = alarm_details

    return result


def asg_join_launch_configuration(parent_attributes, child_attributes):
    name = child_attributes.get('name')
    launch_configuration = parent_attributes.get('launch_configuration')

    if name == launch_configuration:
        return True

    return False


def asg_join_launch_template(parent_attributes, child_attributes):
    name = child_attributes.get('name')
    launch_template = parent_attributes.get('launch_template')

    if name == launch_template['id']:
        return True

    return False


def asg_get_subnet_names(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_autoscaling_group", id, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    return subnet_names


def asg_get_subnet_ids(attributes, arg=None, additional_data=None):
    subnet_names = asg_get_subnet_names(attributes, arg, additional_data)
    if subnet_names:
        return ""
    else:
        return attributes.get(arg)


def asg_get_policy_import_id(attributes, arg=None, additional_data=None):
    autoscaling_group_name = attributes.get("autoscaling_group_name")
    name = attributes.get("name")
    return f"{autoscaling_group_name}/{name}"

### LAUNCHTEMPLATE ###


def lt_get_network_interfaces(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    network_interfaces = attributes.get("network_interfaces", [])
    result = []

    for network_interface in network_interfaces:
        # Create a copy of the items for safe iteration
        items = list(network_interface.items())

        for key, val in items:
            if key == "subnet_id":
                instance_data = get_module_additional_data(
                    "aws_launch_template", id, additional_data)
                subnet_name = instance_data.get("subnet_name", "")
                if subnet_name:
                    network_interface["subnet_name"] = subnet_name
                    network_interface.pop(key)

        result.append(network_interface)
    result = clean_json_values(value=result)
    return result


def launchtemplate_get_block_device_mappings(attributes, arg=None, additional_data=None):
    block_device_mappings = attributes.get("block_device_mappings", [])
    result = []

    for block_device_mapping in block_device_mappings:
        # Create a copy of the items for safe iteration
        items = list(block_device_mapping.items())

        for key, val in items:
            if key == "ebs":
                if val:
                    # Assuming 'ebs' is a list of dictionaries
                    ebs_items = list(val[0].items())
                    for ebs_key, ebs_val in ebs_items:
                        if ebs_key in ["iops", "throughput"] and ebs_val == 0:
                            val[0].pop(ebs_key)
            if not val:
                block_device_mapping.pop(key)

        result.append(block_device_mapping)
    result = clean_json_values(value=result)
    return result

### AURORA ###


def aurora_get_kms_key_alias(attributes, arg=None, additional_data=None):
    identifier = attributes.get("arn")
    instance_data = get_module_additional_data(
        "aws_rds_cluster", identifier, additional_data)
    kms_key_alias = instance_data.get("kms_key_alias", "")
    return kms_key_alias


def aurora_get_kms_key_id(attributes, arg=None, additional_data=None):
    kms_key_id = attributes.get("kms_key_id")
    kms_key_alias = aurora_get_kms_key_alias(
        attributes, arg, additional_data)
    if not kms_key_alias:
        return kms_key_id
    return None


def aurora_get_security_group_ids(attributes, arg=None, additional_data=None):
    identifier = attributes.get("arn")
    instance_data = get_module_additional_data(
        "aws_rds_cluster", identifier, additional_data)
    vpc_security_group_ids = instance_data.get("vpc_security_group_ids", [])
    return vpc_security_group_ids


def aurora_build_instances(attributes, arg=None, additional_data=None):
    result = {}
    identifier = attributes.get("identifier", None)
    result['identifier'] = identifier
    attrs_list = [
        "copy_tags_to_snapshot",
        "preferred_maintenance_window",
        "tags",
    ]
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_rds_cluster_instance", id, additional_data)
    for attr in attrs_list:
        child_value = attributes.get(attr, None)
        parent_value = instance_data.get(attr, None)
        if child_value != parent_value:
            result[attr] = child_value

    instance_class = attributes.get("instance_class", None)
    if instance_class:
        result["instance_class"] = instance_class

    performance_insights_enabled = attributes.get(
        "performance_insights_enabled", False)
    if performance_insights_enabled:
        result["performance_insights_enabled"] = performance_insights_enabled
        performance_insights_kms_key_id = attributes.get(
            "performance_insights_kms_key_id", None)
        if performance_insights_kms_key_id:
            instance_data = get_module_additional_data(
                "aws_rds_cluster_instance", identifier, additional_data)
            performance_insights_kms_key_alias = instance_data.get(
                "performance_insights_kms_key_alias", "")
            if performance_insights_kms_key_alias:
                result["performance_insights_kms_key_alias"] = performance_insights_kms_key_alias
            else:
                result["performance_insights_kms_key_id"] = performance_insights_kms_key_id
        performance_insights_retention_period = attributes.get(
            "performance_insights_retention_period", None)
        if performance_insights_retention_period:
            result["performance_insights_retention_period"] = performance_insights_retention_period
    publicly_accessible = attributes.get("publicly_accessible", False)
    if publicly_accessible:
        result["publicly_accessible"] = publicly_accessible

    monitoring_interval = attributes.get("monitoring_interval", 0)
    if monitoring_interval != 0:
        result["monitoring_interval"] = monitoring_interval

    monitoring_role_arn = attributes.get("monitoring_role_arn", 0)
    if monitoring_role_arn:
        result["monitoring_role_arn"] = monitoring_role_arn

    apply_immediately = attributes.get("apply_immediately", False)
    if apply_immediately:
        result["apply_immediately"] = apply_immediately

    auto_minor_version_upgrade = attributes.get(
        "auto_minor_version_upgrade", True)
    if not auto_minor_version_upgrade:
        result["auto_minor_version_upgrade"] = auto_minor_version_upgrade

    promotion_tier = attributes.get("promotion_tier", None)
    if promotion_tier:
        result["promotion_tier"] = promotion_tier

    db_parameter_group_name = attributes.get("db_parameter_group_name", None)
    if db_parameter_group_name:
        result["db_parameter_group_name"] = db_parameter_group_name
    return {identifier: result}


def aurora_build_cluster_endpoint(attributes, arg=None, additional_data=None):
    result = {}
    identifier = attributes.get("cluster_endpoint_identifier", None)
    type = attributes.get("custom_endpoint_type", None)
    if type:
        result["type"] = type
    excluded_members = attributes.get('excluded_members', [])
    if excluded_members:
        result['excluded_members'] = excluded_members
    static_members = attributes.get('static_members', [])
    if static_members:
        result['static_members'] = static_members
    tags = attributes.get('tags', {})
    if tags:
        result['tags'] = tags

    return {identifier: result}


def aurora_build_cluster_role_association(attributes, arg=None, additional_data=None):
    result = {}
    role_arn = attributes.get("role_arn", None)
    feature_name = attributes.get("feature_name", None)
    if feature_name:
        result["feature_name"] = feature_name

    return {role_arn: result}


def aurora_build_resource_id(attributes):
    resource_id = attributes.get("resource_id", None)
    return f"cluster:{resource_id}"


def aurora_get_subnet_names(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_db_subnet_group", id, additional_data)
    subnet_names = instance_data.get("subnet_names", [])
    return subnet_names


def aurora_get_subnet_ids(attributes, arg=None, additional_data=None):
    subnet_names = aurora_get_subnet_names(attributes, arg, additional_data)
    if subnet_names:
        return ""
    else:
        return attributes.get("subnet_ids")


def aurora_get_vpc_name_by_subnet(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_db_subnet_group", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def aurora_get_vpc_id_by_subnet(attributes, arg=None, additional_data=None):
    vpc_name = aurora_get_vpc_name_by_subnet(
        attributes, arg, additional_data)
    if not vpc_name:
        return attributes.get(arg)
    else:
        return ""


def aurora_get_vpc_name_by_group(attributes, arg=None, additional_data=None):
    arn = attributes.get("arn")
    instance_data = get_module_additional_data(
        "aws_rds_cluster", arn, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def aurora_get_vpc_id_by_group(attributes, arg=None, additional_data=None):
    vpc_name = aurora_get_vpc_name_by_group(attributes, arg, additional_data)
    vpc_id = ""
    if not vpc_name:
        arn = attributes.get("arn")
        instance_data = get_module_additional_data(
            "aws_rds_cluster", arn, additional_data)
        vpc_id = instance_data.get("vpc_id", "")
    return vpc_id


### VPC ###
# def vpc_get_dhcp_options_domain_name(attributes, arg=None, additional_data=None):
#     assoc_id = attributes.get('id')
#     return self.dhcp_options_domain_name[assoc_id]

def vpc_is_subnet_public(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_subnet", id, additional_data)
    is_public = instance_data.get("is_public", False)
    return is_public


def vpc_is_subnet_private(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_subnet", id, additional_data)
    is_private = instance_data.get("is_private", False)
    return is_private

# def vpc_init_fields(attributes):
#     self.private_subnets = {}
#     self.public_subnets = {}
#     self.public_route_table_ids = {}
#     self.private_route_table_ids = {}
#     self.public_nat_gateway_ids = {}
#     self.private_route_tables = {}
#     self.network_acl_ids = {}
#     self.network_acls = {}

#     return None


def vpc_add_public_subnet(attributes, arg=None, additional_data=None):
    # subnet_id = attributes.get('id')
    cidr_block = attributes.get('cidr_block')
    availability_zone = attributes.get('availability_zone')
    tags = attributes.get('tags', {})
    ipv6_cidr_block = attributes.get('ipv6_cidr_block')
    assign_ipv6_address_on_creation = attributes.get(
        'assign_ipv6_address_on_creation')
    enable_dns64 = attributes.get('enable_dns64')
    enable_resource_name_dns_aaaa_record_on_launch = attributes.get(
        'enable_resource_name_dns_aaaa_record_on_launch')
    enable_resource_name_dns_a_record_on_launch = attributes.get(
        'enable_resource_name_dns_a_record_on_launch')
    ipv6_native = attributes.get('ipv6_native')
    map_public_ip_on_launch = attributes.get('map_public_ip_on_launch')
    private_dns_hostname_type_on_launch = attributes.get(
        'private_dns_hostname_type_on_launch')
    # self.public_subnets[subnet_id] = {
    result = {
        cidr_block: {
            'az': availability_zone,
            'ipv6_cidr_block': ipv6_cidr_block,
            'tags': tags,
            # 'route_tables': [],
            # 'nat_gateway': {},
            'assign_ipv6_address_on_creation': assign_ipv6_address_on_creation,
            'enable_dns64': enable_dns64,
            'enable_resource_name_dns_aaaa_record_on_launch': enable_resource_name_dns_aaaa_record_on_launch,
            'enable_resource_name_dns_a_record_on_launch': enable_resource_name_dns_a_record_on_launch,
            'ipv6_native': ipv6_native,
            'map_public_ip_on_launch': map_public_ip_on_launch,
            'private_dns_hostname_type_on_launch': private_dns_hostname_type_on_launch,
        }
    }
    return result


def vpc_add_nat_gateway(attributes, arg=None, additional_data=None):
    tags = attributes.get('tags', {})
    nat_gateway_name = None
    for key, value in tags.items():
        if key == 'Name':
            nat_gateway_name = value
            break
    if not nat_gateway_name:
        nat_gateway_id = attributes.get('id')
        nat_gateway_name = nat_gateway_id

    id = attributes.get('id')
    instance_data = get_module_additional_data(
        "aws_nat_gateway", id, additional_data)
    subnet_cidr = instance_data.get("subnet_cidr", "")

    result = {}
    result[nat_gateway_name] = {}
    result[nat_gateway_name]['subnet_cidr'] = subnet_cidr
    result[nat_gateway_name]['tags'] = tags

    return result


# def vpc_add_network_acl(attributes, arg=None, additional_data=None):
#     nacl_id = attributes.get('id')
#     if nacl_id not in self.network_acl_ids:
#         nacl_name = 'network_acl_' + \
#             str(len(self.network_acl_ids))
#         self.network_acl_ids[nacl_id] = nacl_name
#     else:
#         nacl_name = self.network_acl_ids[nacl_id]

#     subnet_ids_ = attributes.get('subnet_ids')
#     subnet_list_name = []
#     for subnet_id in subnet_ids_:
#         if subnet_id in self.public_subnets:
#             for key in self.public_subnets[subnet_id].keys():
#                 subnet_list_name.append(key)
#         elif subnet_id in self.private_subnets:
#             for key in self.private_subnets[subnet_id].keys():
#                 subnet_list_name.append(key)
#     self.network_acls[nacl_name] = {
#         'subnet_ids': subnet_list_name, 'tags': attributes.get('tags', {}), 'ingress_rules': {}, 'egress_rules': {}}
#     return {nacl_name: self.network_acls[nacl_name]}

# def vpc_get_network_acl_id(attributes, arg=None, additional_data=None):
#     nacl_id = attributes.get(arg)
#     nacl_name = self.network_acl_ids[nacl_id]
#     return nacl_name

# def vpc_get_network_acl_rule_id(attributes, arg=None, additional_data=None):
#     nacl_id = attributes.get(arg)
#     nacl_name = self.network_acl_ids[nacl_id]
#     return nacl_name+'_'+str(attributes.get('rule_number'))

# def vpc_add_network_acl_ingress_rule(attributes, arg=None, additional_data=None):
#     nacl_id = attributes.get('network_acl_id')
#     nacl_name = self.network_acl_ids[nacl_id]
#     rule = {}
#     # Rulenumber must be in range 1..32766
#     if attributes.get('rule_number') < 32767:
#         for k in ['rule_number', 'protocol', 'rule_action', 'cidr_block',
#                     'icmp_code', 'icmp_type', 'ipv6_cidr_block', 'from_port', 'to_port']:
#             val = attributes.get(k)
#             if val not in [None, "", [], {}]:
#                 rule[k] = val
#         self.network_acls[nacl_name]['ingress_rules'][rule['rule_number']] = rule
#     return {nacl_name: self.network_acls[nacl_name]}

# def vpc_add_network_acl_egress_rule(attributes, arg=None, additional_data=None):
#     nacl_id = attributes.get('network_acl_id')
#     nacl_name = self.network_acl_ids[nacl_id]
#     rule = {}

#     # Rulenumber must be in range 1..32766
#     if attributes.get('rule_number') < 32767:
#         for k in ['rule_number', 'protocol', 'rule_action', 'cidr_block',
#                     'icmp_code', 'icmp_type', 'ipv6_cidr_block', 'from_port', 'to_port']:
#             val = attributes.get(k)
#             if val not in [None, "", [], {}]:
#                 rule[k] = val
#         self.network_acls[nacl_name]['egress_rules'][rule['rule_number']] = rule
#     return {nacl_name: self.network_acls[nacl_name]}

def vpc_default_route_table_routes(attributes, arg=None, additional_data=None):
    input_routes = attributes.get('route', [])

    # Filter out entries with empty string values
    filtered_routes = []
    for route in input_routes:
        filtered_route = {k: v for k, v in route.items() if v != ""}
        filtered_routes.append(filtered_route)

    return filtered_routes


def vpc_add_eip(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data("aws_eip", id, additional_data)
    nat_gateway_name = instance_data.get("nat_gateway_name", "")
    result = {}
    result[nat_gateway_name] = {}
    result[nat_gateway_name]['eip_tags'] = attributes.get('tags', {})
    return result

# def get_public_route_table_name(route_table_id):
#     if route_table_id not in self.public_route_table_ids:
#         route_table_name = 'public_route_table_' + \
#             str(len(self.public_route_table_ids))
#         self.public_route_table_ids[route_table_id] = route_table_name
#     else:
#         route_table_name = self.public_route_table_ids[route_table_id]

#     return route_table_name


def vpc_add_route_table_association(attributes, arg=None, additional_data=None):
    route_table_id = attributes.get('route_table_id')
    route_table_name = route_table_id
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_route_table_association", id, additional_data)
    # route_table_name = instance_data.get("route_table_name", "")
    # if not route_table_name:
    #     route_table_name = route_table_id
    subnet_cidr = instance_data.get("subnet_cidr", "")
    result = {}
    result[route_table_name] = {"associations": {subnet_cidr: True}}
    return result


def vpc_add_route_table(attributes, arg=None, additional_data=None):
    route_table_id = attributes.get('id')
    route_table_name = route_table_id
    tags = attributes.get('tags', {})
    # for key, value in tags.items():
    #     if key == 'Name':
    #         route_table_name = value
    #         break
    # if not route_table_name:
    #     route_table_id = attributes.get('id')
    #     route_table_name = route_table_id

    tags = escape_dict_contents(tags)
    return {route_table_name: {"tags": tags}}


def vpc_get_route_table_name(attributes, arg=None, additional_data=None):
    route_table_id = attributes.get('id')
    route_table_name = route_table_id
    # tags = attributes.get('tags', {})
    # for key, value in tags.items():
    #     if key == 'Name':
    #         route_table_name = value
    #         break
    # if not route_table_name:
    #     route_table_id = attributes.get('id')
    #     route_table_name = route_table_id
    return route_table_name

# def vpc_get_route_table_route_id(attributes, arg=None, additional_data=None):
#     id = attributes.get("id")
#     instance_data = get_module_additional_data("aws_route", id, additional_data)
#     route_table_name = instance_data.get("route_table_name", "")
#     if not route_table_name:
#         route_table_id = attributes.get('route_table_id')
#         route_table_name = route_table_id
#     return route_table_name+'_'+str(attributes.get('rule_number'))


def vpc_add_route(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_route", id, additional_data)
    route_table_id = attributes.get('route_table_id')
    route_table_name = route_table_id
    # route_table_name = instance_data.get("route_table_name", "")
    # if not route_table_name:
    #     route_table_id = attributes.get('route_table_id')
    #     route_table_name = route_table_id
    tags = attributes.get('tags', {})
    tags = escape_dict_contents(tags)
    result = {}
    result[route_table_name] = {}
    result[route_table_name]['routes'] = {}
    result[route_table_name]['routes'][id] = {}
    destination_cidr_block = attributes.get('destination_cidr_block', "")
    if destination_cidr_block:
        result[route_table_name]['routes'][id]["destination_cidr_block"] = destination_cidr_block
    destination_ipv6_cidr_block = attributes.get(
        'destination_ipv6_cidr_block', "")
    if destination_ipv6_cidr_block:
        result[route_table_name]['routes'][id]["destination_ipv6_cidr_block"] = destination_ipv6_cidr_block
    gateway_id = attributes.get('gateway_id')
    if gateway_id:
        result[route_table_name]['routes'][id]["igw"] = True
    nat_gateway_id = attributes.get('nat_gateway_id')
    nat_gateway_name = None
    if nat_gateway_id:
        nat_gateway_name = instance_data.get("nat_gateway_name", "")
        if not nat_gateway_name:
            nat_gateway_name = nat_gateway_id
        result[route_table_name]['routes'][id]["nat_gateway_name"] = nat_gateway_name
    return result


def vpc_get_route_import_id(attributes, arg=None, additional_data=None):
    route_table_id = attributes.get('route_table_id')
    destination_cidr_block = attributes.get('destination_cidr_block', "")
    if destination_cidr_block:
        return route_table_id+'_'+destination_cidr_block
    destination_ipv6_cidr_block = attributes.get(
        'destination_ipv6_cidr_block', "")
    if destination_ipv6_cidr_block:
        return route_table_id+'_'+destination_ipv6_cidr_block

# def vpc_get_aws_route_import_id(attributes, arg=None, additional_data=None):
#     id = attributes.get("id")
#     instance_data = get_module_additional_data("aws_route", id, additional_data)
#     route_table_name = instance_data.get("route_table_name", "")
#     if not route_table_name:
#         route_table_id = attributes.get('route_table_id')
#         route_table_name = route_table_id


def vpc_get_nat_gateway_index(attributes, arg=None, additional_data=None):
    tags = attributes.get('tags', {})
    nat_gateway_name = None
    for key, value in tags.items():
        if key == 'Name':
            nat_gateway_name = value
            break
    if not nat_gateway_name:
        nat_gateway_id = attributes.get('id')
        nat_gateway_name = nat_gateway_id
    return nat_gateway_name


def vpc_get_eip_index(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data("aws_eip", id, additional_data)
    nat_gateway_name = instance_data.get("nat_gateway_name", "")
    return nat_gateway_name


def vpc_get_route_table_association_index(attributes, arg=None, additional_data=None):
    route_table_id = attributes.get('route_table_id')
    route_table_name = route_table_id
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_route_table_association", id, additional_data)
    # route_table_name = instance_data.get("route_table_name", "")
    # if not route_table_name:
    #     route_table_name = route_table_id
    subnet_cidr = instance_data.get("subnet_cidr", "")
    return subnet_cidr+"-"+route_table_name

# def vpc_join_igw_route_table_id(parent_attributes, child_attributes):
#     gateway_id = parent_attributes.get('id')
#     route = child_attributes.get('route')
#     if route:
#         if route[0].get('gateway_id', None) == gateway_id:
#             return True
#     return False

# def vpc_get_public_route_table_id(attributes, arg=None, additional_data=None):
#     route_table_id = attributes.get(arg)
#     route_table_name = self.get_public_route_table_name(route_table_id)
#     return route_table_name


def vpc_add_private_subnet(attributes, arg=None, additional_data=None):
    cidr_block = attributes.get('cidr_block')
    availability_zone = attributes.get('availability_zone')
    tags = attributes.get('tags', {})
    ipv6_cidr_block = attributes.get('ipv6_cidr_block')
    assign_ipv6_address_on_creation = attributes.get(
        'assign_ipv6_address_on_creation')
    enable_dns64 = attributes.get('enable_dns64')
    enable_resource_name_dns_aaaa_record_on_launch = attributes.get(
        'enable_resource_name_dns_aaaa_record_on_launch')
    enable_resource_name_dns_a_record_on_launch = attributes.get(
        'enable_resource_name_dns_a_record_on_launch')
    ipv6_native = attributes.get('ipv6_native')
    private_dns_hostname_type_on_launch = attributes.get(
        'private_dns_hostname_type_on_launch')
    map_public_ip_on_launch = attributes.get('map_public_ip_on_launch')

    result = {
        cidr_block: {
            'az': availability_zone,
            'ipv6_cidr_block': ipv6_cidr_block,
            'tags': tags,
            'route_tables': [],
            'assign_ipv6_address_on_creation': assign_ipv6_address_on_creation,
            'enable_dns64': enable_dns64,
            'enable_resource_name_dns_aaaa_record_on_launch': enable_resource_name_dns_aaaa_record_on_launch,
            'enable_resource_name_dns_a_record_on_launch': enable_resource_name_dns_a_record_on_launch,
            'ipv6_native': ipv6_native,
            'private_dns_hostname_type_on_launch': private_dns_hostname_type_on_launch,
            'map_public_ip_on_launch': map_public_ip_on_launch,
        }
    }
    return result

# def vpc_add_private_route_table_association(attributes, arg=None, additional_data=None):
#     route_table_id = attributes.get('route_table_id')
#     if route_table_id not in self.private_route_table_ids:
#         route_table_name = 'private_route_table_' + \
#             str(len(self.private_route_table_ids))
#         self.private_route_table_ids[route_table_id] = route_table_name
#     else:
#         route_table_name = self.private_route_table_ids[route_table_id]

#     subnet_id = attributes.get('subnet_id')
#     if 'association' not in self.private_subnets:
#         self.private_subnets['association'] = {}
#     for key in self.private_subnets[subnet_id].keys():
#         self.private_subnets[subnet_id][key]['route_tables'].append(
#             route_table_name)
#     return self.private_subnets[subnet_id]

# def vpc_add_private_route_table(attributes, arg=None, additional_data=None):
#     route_table_id = attributes.get('id')
#     route_table_name = self.private_route_table_ids[route_table_id]
#     tags = attributes.get('tags', {})
    # tags = self.escape_dict_contents(tags)
    # self.private_route_tables[route_table_name] = {
    #     "tags": tags, "nat_gateway_attached": ""}
    # return {route_table_name: self.private_route_tables[route_table_name]}

# def vpc_add_nat_gateway_private_route(attributes, arg=None, additional_data=None):
#     route_table_id = attributes.get('route_table_id')
#     # print("nat_gateway_id", attributes.get('nat_gateway_id'))
#     if route_table_id in self.private_route_table_ids:
#         route_table_name = self.private_route_table_ids[route_table_id]
#         nat_gateway_id = attributes.get('nat_gateway_id')
#         nat_gateway_name = self.public_nat_gateway_ids[nat_gateway_id]

#         self.private_route_tables[route_table_name]["nat_gateway_attached"] = nat_gateway_name
#         return {route_table_name: self.private_route_tables[route_table_name]}
#     return {}

# def vpc_get_nat_gateway_private_route_id(attributes, arg=None, additional_data=None):
#     route_table_id = attributes.get('route_table_id')
#     if route_table_id in self.private_route_table_ids:
#         route_table_name = self.private_route_table_ids[route_table_id]
#         return route_table_name+"-0.0.0.0/0"
#     return ""

# def vpc_get_private_route_table_association_index(attributes, arg=None, additional_data=None):
#     route_table_id = attributes.get('route_table_id')
#     route_table_name = self.private_route_table_ids[route_table_id]
#     subnet_id = attributes.get('subnet_id')
#     for key in self.private_subnets[subnet_id].keys():
#         return key+"-"+route_table_name


def vpc_get_route_table_association_import_id(attributes, arg=None, additional_data=None):
    route_table_id = attributes.get('route_table_id')
    subnet_id = attributes.get('subnet_id')
    return subnet_id+"/"+route_table_id


# def vpc_get_private_route_table_id(attributes, arg=None, additional_data=None):
#     route_table_id = attributes.get(arg)
#     route_table_name = self.private_route_table_ids[route_table_id]
#     return route_table_name

def vpc_build_aws_flow_logs(attributes, arg=None, additional_data=None):
    log_destination = attributes.get('log_destination')
    key = log_destination
    if "s3" in log_destination:
        key = key.split(":")[-1]
    result = {key: {}}
    for k in ['log_destination', 'log_destination_type', 'log_format',
              'iam_role_arn', 'traffic_type', 'max_aggregation_interval',
              'destination_options',  'log_group_name', 'tags']:
        val = attributes.get(k)
        if isinstance(val, str):
            val = val.replace('${', '$${')
        result[key][k] = val
    return result


def escape_dict_contents(data_dict):
    # convert data_dict to str
    data_str = json.dumps(data_dict)
    data_str = data_str.replace('${', '$${')
    # convert data_str back to dict
    result = json.loads(data_str)
    return result


def vpc_format_ingress_rules(attributes, arg=None, additional_data=None):
    ingress_dict = attributes.get('ingress', [])
    formatted_ingress = []
    for ingress_rule in ingress_dict:
        ingress_rule['cidr_blocks'] = ','.join(ingress_rule['cidr_blocks'])
        ingress_rule['ipv6_cidr_blocks'] = ','.join(
            ingress_rule['ipv6_cidr_blocks'])
        ingress_rule['prefix_list_ids'] = ','.join(
            ingress_rule['prefix_list_ids'])
        ingress_rule['security_groups'] = ','.join(
            ingress_rule['security_groups'])
        formatted_ingress.append(ingress_rule)
    return formatted_ingress


def vpc_format_egress_rules(attributes, arg=None, additional_data=None):
    egress_dict = attributes.get('egress', [])
    formatted_egress = []
    for egress_rule in egress_dict:
        egress_rule['cidr_blocks'] = ','.join(egress_rule['cidr_blocks'])
        egress_rule['ipv6_cidr_blocks'] = ','.join(
            egress_rule['ipv6_cidr_blocks'])
        egress_rule['prefix_list_ids'] = ','.join(
            egress_rule['prefix_list_ids'])
        egress_rule['security_groups'] = ','.join(
            egress_rule['security_groups'])
        formatted_egress.append(egress_rule)
    return formatted_egress


def vpc_format_network_acl_rules(attributes, arg=None, additional_data=None):
    input_dict = attributes.get(arg, [])
    formatted_input = []
    for input_rule in input_dict:
        # create a copy so as not to mutate the original rule
        input_rule = input_rule.copy()
        for key in ['cidr_block', 'ipv6_cidr_block', 'icmp_code', 'icmp_type']:
            if key in input_rule and input_rule[key] == "":
                # remove the key-value pair from the dictionary
                del input_rule[key]
            elif key in input_rule:
                input_rule[key] = str(input_rule[key])
        formatted_input.append(input_rule)
    return formatted_input

# def vpc_is_network_acl_rule_egress(attributes, arg=None, additional_data=None):
#     return attributes.get('egress', False)

# def vpc_is_network_acl_rule_ingress(attributes, arg=None, additional_data=None):
#     return not attributes.get('egress', False)

# def vpc_aws_network_acl_rule_import_id(attributes, arg=None, additional_data=None):
#     return attributes.get('network_acl_id') + ":" + str(attributes.get('rule_number')) + ":" + str(attributes.get('protocol')) + ":" + str(attributes.get('egress'))


### CLIENT VPN ###

def get_vpc_name_client_vpn(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_ec2_client_vpn_endpoint", id, additional_data)
    vpc_name = instance_data.get("vpc_name", "")
    return vpc_name


def get_vpc_id_client_vpn(attributes, arg=None, additional_data=None):
    vpc_name = get_vpc_name_client_vpn(attributes, arg, additional_data)
    if not vpc_name:
        vpc_id = attributes.get("vpc_id", "")
        return vpc_id
    else:
        return ""


# def client_vpn_get_subnet_name(attributes, arg=None, additional_data=None):
#     id = attributes.get("id")
#     instance_data = get_module_additional_data(
#         "aws_ec2_client_vpn_network_association", id, additional_data)
#     subnet_name = instance_data.get("subnet_name", [])
#     return subnet_name


# def client_vpn_get_subnet_id(attributes, arg=None, additional_data=None):
#     subnet_name = client_vpn_get_subnet_name(attributes, arg, additional_data)
#     if subnet_name:
#         return ""
#     else:
#         return attributes.get("subnet_id")


def client_vpn_network_association_import_id(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    client_vpn_endpoint_id = attributes.get("client_vpn_endpoint_id")
    return f"{client_vpn_endpoint_id},{id}"


def client_vpn_network_association_second_index(attributes, arg=None, additional_data=None):
    subnet_id = client_vpn_network_association_get_subnet_ids(
        attributes, arg, additional_data)
    if subnet_id:
        return subnet_id[0]
    subnet_name = client_vpn_network_association_get_subnet_names(
        attributes, arg, additional_data)
    if subnet_name:
        return subnet_name[0]


def client_vpn_authorization_rule_import_id(attributes, arg=None, additional_data=None):
    client_vpn_endpoint_id = attributes.get("client_vpn_endpoint_id")
    target_network_cidr = attributes.get("target_network_cidr")
    return f"{client_vpn_endpoint_id},{target_network_cidr}"


def client_vpn_route_get_target_vpc_subnet_name(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_ec2_client_vpn_route", id, additional_data)
    subnet_name = instance_data.get("subnet_name", [])
    return subnet_name


def client_vpn_route_import_id(attributes, arg=None, additional_data=None):
    client_vpn_endpoint_id = attributes.get("client_vpn_endpoint_id")
    target_subnet_id = attributes.get("target_vpc_subnet_id")
    destination_cidr = attributes.get("destination_cidr_block")
    return f"{client_vpn_endpoint_id},{target_subnet_id},{destination_cidr}"


def client_vpn_route_get_target_vpc_subnet_id(attributes, arg=None, additional_data=None):
    subnet_name = client_vpn_route_get_target_vpc_subnet_name(
        attributes, arg, additional_data)
    if subnet_name:
        return ""
    else:
        return attributes.get("subnet_id")


def client_vpn_network_association_get_subnet_names(attributes, arg=None, additional_data=None):
    id = attributes.get("id")
    instance_data = get_module_additional_data(
        "aws_ec2_client_vpn_network_association", id, additional_data)
    subnet_name = instance_data.get("subnet_name")
    return [subnet_name]


def client_vpn_network_association_get_subnet_ids(attributes, arg=None, additional_data=None):
    subnet_name = client_vpn_network_association_get_subnet_names(
        attributes, arg, additional_data)
    if subnet_name:
        return []
    else:
        return [attributes.get("subnet_id")]


def client_vpn_authorization_rule_get_rules(attributes, arg=None, additional_data=None):
    result = []
    target_network_cidr = attributes.get("target_network_cidr")
    access_group_id = attributes.get("access_group_id")
    authorize_all_groups = attributes.get("authorize_all_groups")
    description = attributes.get("description")
    result.append({
        "target_network_cidr": target_network_cidr,
        "access_group_id": access_group_id,
        "authorize_all_groups": authorize_all_groups,
        "description": description
    })
    result = clean_json_values(value=result)
    return result


def client_vpn_route_get_routes(attributes, arg=None, additional_data=None):
    result = []
    destination_cidr_block = attributes.get("destination_cidr_block")
    description = attributes.get("description")
    target_vpc_subnet_name = client_vpn_route_get_target_vpc_subnet_name(
        attributes, arg, additional_data)
    target_vpc_subnet_id = client_vpn_route_get_target_vpc_subnet_id(
        attributes, arg, additional_data)
    result.append({
        "destination_cidr_block": destination_cidr_block,
        "description": description,
        "target_vpc_subnet_name": target_vpc_subnet_name,
        "target_vpc_subnet_id": target_vpc_subnet_id
    })
    result = clean_json_values(value=result)
    return result


def client_vpn_route_second_index(attributes, arg=None, additional_data=None):
    target_vpc_subnet_id = attributes.get("target_vpc_subnet_id")
    destination_cidr_block = attributes.get("destination_cidr_block")
    return f"{target_vpc_subnet_id}_{destination_cidr_block}"
