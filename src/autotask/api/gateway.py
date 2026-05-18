"""
API 网关
v1 预留：基础接口定义
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio


class HTTPMethod(str, Enum):
    """HTTP 方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"


class APIRouteType(str, Enum):
    """路由类型"""
    SYNC = "sync"
    ASYNC = "async"
    STREAM = "stream"


@dataclass
class APIRoute:
    """
    API 路由定义
    """
    path: str
    method: HTTPMethod
    handler: Callable
    route_type: APIRouteType = APIRouteType.SYNC
    summary: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    middleware: List[Callable] = field(default_factory=list)
    auth_required: bool = False
    
    @property
    def endpoint(self) -> str:
        """完整端点"""
        return f"{self.method.value} {self.path}"


@dataclass
class APIResponse:
    """API 响应"""
    status_code: int = 200
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "data": self.data,
            "message": self.message,
            "error": self.error,
        }


@dataclass
class APIRequest:
    """API 请求"""
    method: HTTPMethod
    path: str
    query_params: Dict[str, Any] = field(default_factory=dict)
    path_params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    user: Optional[Dict[str, Any]] = None


class APIRouter:
    """
    API 路由组
    
    用于组织相关路由
    """
    
    def __init__(self, prefix: str = "", tags: Optional[List[str]] = None):
        self.prefix = prefix
        self.tags = tags or []
        self.routes: List[APIRoute] = []
        self._routers: List["APIRouter"] = []
    
    def add_route(
        self,
        path: str,
        method: HTTPMethod,
        handler: Callable,
        **kwargs
    ) -> APIRoute:
        """添加路由"""
        full_path = f"{self.prefix}{path}"
        route = APIRoute(
            path=full_path,
            method=method,
            handler=handler,
            tags=self.tags + kwargs.get("tags", []),
            **kwargs
        )
        self.routes.append(route)
        return route
    
    def get(self, path: str, **kwargs) -> Callable:
        """添加 GET 路由"""
        def decorator(func: Callable) -> Callable:
            self.add_route(path, HTTPMethod.GET, func, **kwargs)
            return func
        return decorator
    
    def post(self, path: str, **kwargs) -> Callable:
        """添加 POST 路由"""
        def decorator(func: Callable) -> Callable:
            self.add_route(path, HTTPMethod.POST, func, **kwargs)
            return func
        return decorator
    
    def put(self, path: str, **kwargs) -> Callable:
        """添加 PUT 路由"""
        def decorator(func: Callable) -> Callable:
            self.add_route(path, HTTPMethod.PUT, func, **kwargs)
            return func
        return decorator
    
    def delete(self, path: str, **kwargs) -> Callable:
        """添加 DELETE 路由"""
        def decorator(func: Callable) -> Callable:
            self.add_route(path, HTTPMethod.DELETE, func, **kwargs)
            return func
        return decorator
    
    def include_router(self, router: "APIRouter") -> None:
        """包含子路由"""
        self._routers.append(router)
    
    def get_all_routes(self) -> List[APIRoute]:
        """获取所有路由"""
        routes = list(self.routes)
        for router in self._routers:
            routes.extend(router.get_all_routes())
        return routes


class APIGateway:
    """
    API 网关
    
    职责：
    - 路由管理
    - 请求分发
    - 响应格式化
    - 中间件支持
    - OpenAPI 规范生成
    """
    
    def __init__(self, title: str = "AutoTask API", version: str = "1.0"):
        self.title = title
        self.version = version
        self._routers: List[APIRouter] = []
        self._middleware: List[Callable] = []
        self._route_map: Dict[str, Dict[HTTPMethod, APIRoute]] = {}
    
    def add_router(self, router: APIRouter) -> None:
        """添加路由组"""
        self._routers.append(router)
        self._update_route_map(router)
    
    def add_middleware(self, middleware: Callable) -> None:
        """添加中间件"""
        self._middleware.append(middleware)
    
    def _update_route_map(self, router: APIRouter) -> None:
        """更新路由映射"""
        for route in router.get_all_routes():
            if route.path not in self._route_map:
                self._route_map[route.path] = {}
            self._route_map[route.path][route.method] = route
    
    async def handle_request(self, request: APIRequest) -> APIResponse:
        """
        处理请求
        
        Args:
            request: API 请求
            
        Returns:
            API 响应
        """
        # 匹配路由
        path = request.path
        if path not in self._route_map:
            return APIResponse(
                status_code=404,
                error="Not Found",
                message=f"Route {request.method.value} {path} not found",
            )
        
        method_routes = self._route_map[path]
        if request.method not in method_routes:
            return APIResponse(
                status_code=405,
                error="Method Not Allowed",
                message=f"Method {request.method.value} not allowed for {path}",
            )
        
        route = method_routes[request.method]
        
        # 执行中间件
        for middleware in self._middleware:
            result = middleware(request)
            if result is not None:
                return result
        
        # 执行路由中间件
        for mw in route.middleware:
            result = mw(request)
            if result is not None:
                return result
        
        # 认证检查
        if route.auth_required and not request.user:
            return APIResponse(
                status_code=401,
                error="Unauthorized",
                message="Authentication required",
            )
        
        # 执行处理器
        try:
            if route.route_type == APIRouteType.ASYNC:
                result = await route.handler(request)
            elif route.route_type == APIRouteType.STREAM:
                result = await route.handler(request)  # 流式处理器
            else:
                result = route.handler(request)
            
            if isinstance(result, APIResponse):
                return result
            
            return APIResponse(
                status_code=200,
                data=result,
            )
        
        except Exception as e:
            return APIResponse(
                status_code=500,
                error="Internal Server Error",
                message=str(e),
            )
    
    def generate_openapi(self) -> Dict[str, Any]:
        """
        生成 OpenAPI 规范
        
        Returns:
            OpenAPI 文档
        """
        paths: Dict[str, Any] = {}
        
        for path, methods in self._route_map.items():
            path_item = {}
            for method, route in methods.items():
                path_item[method.value.lower()] = {
                    "summary": route.summary,
                    "description": route.description,
                    "tags": route.tags,
                    "parameters": route.parameters,
                    "requestBody": route.request_body,
                    "responses": route.responses,
                }
            paths[path] = path_item
        
        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
            },
            "paths": paths,
        }
    
    def list_routes(self) -> List[str]:
        """列出所有路由"""
        routes = []
        for path, methods in self._route_map.items():
            for method in methods.keys():
                routes.append(f"{method.value} {path}")
        return routes


# 预定义中间件
async def logging_middleware(request: APIRequest) -> Optional[APIResponse]:
    """日志中间件"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"{request.method.value} {request.path}")
    return None


async def cors_middleware(request: APIRequest) -> Optional[APIResponse]:
    """CORS 中间件"""
    if request.method == HTTPMethod.OPTIONS:
        return APIResponse(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    return None


# 错误响应辅助函数
def success_response(data: Any = None, message: str = "Success") -> APIResponse:
    """成功响应"""
    return APIResponse(
        status_code=200,
        data=data,
        message=message,
    )


def created_response(data: Any = None, message: str = "Created") -> APIResponse:
    """创建成功响应"""
    return APIResponse(
        status_code=201,
        data=data,
        message=message,
    )


def error_response(
    status_code: int,
    error: str,
    message: str = ""
) -> APIResponse:
    """错误响应"""
    return APIResponse(
        status_code=status_code,
        error=error,
        message=message,
    )
