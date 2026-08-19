from flask import Blueprint,jsonify,request
from ..extensions import db
from ..models import Application,ApiEndpointDefinition
from ..services.proxy_service import forward,ProxyError
bp=Blueprint('gateway',__name__,url_prefix='/gateway')
@bp.route('/<app_slug>/<endpoint_slug>',methods=['GET','POST','PUT','PATCH','DELETE'])
def execute_endpoint(app_slug,endpoint_slug):
    app=Application.query.filter_by(slug=app_slug,active=True).first_or_404(); endpoint=ApiEndpointDefinition.query.filter_by(application_id=app.id,slug=endpoint_slug,enabled=True).first_or_404()
    if endpoint.method.upper()!=request.method.upper():return jsonify(error='method_not_allowed'),405
    try:
        status,headers,payload=forward(endpoint.profile,endpoint.method,endpoint.path,query=request.args.to_dict(flat=True),headers={'Authorization':request.headers.get('Authorization',''),'X-Request-ID':request.headers.get('X-Request-ID','')},json_body=request.get_json(silent=True) if request.method not in {'GET','DELETE'} else None)
    except ProxyError as exc:return jsonify(error='proxy_blocked',message=str(exc)),403
    except Exception: db.session.rollback(); return jsonify(error='upstream_unavailable'),502
    return jsonify(payload) if isinstance(payload,(dict,list)) else (payload,status,{'Content-Type':headers.get('content-type','text/plain')})
