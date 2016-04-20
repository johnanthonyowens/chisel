var chips = (function () {
    var module = {};

    module.nbsp = String.fromCharCode(160);

    module.render = function (parent, elems, clear) {
        if (clear) {
            parent.innerHTML = '';
        }
        return appendNodes(parent, elems);
    };

    module.node = function (elem) {
        let node_ = elem.text ? document.createTextNode(elem.text) : document.createElement(elem.tag);
        if (elem.attrs) {
            for (let attr in elem.attrs) {
                let value = elem.attrs[attr];
                if (value) {
                    node_.setAttribute(attr, value);
                }
            }
        }
        return appendNodes(node_, elem.elems);
    };

    function appendNodes(parent, elems) {
        if (module.isArray(elems)) {
            for (let iElem = 0; iElem < elems.length; iElem++) {
                appendNodes(parent, elems[iElem]);
            }
        } else if (elems) {
            parent.appendChild(module.node(elems));
        }
        return parent;
    }

    module.elem = function (tag, attrsOrElems, elems) {
        let attrs = module.isObject(attrsOrElems) ? attrsOrElems : undefined;
        return {
            tag: tag,
            attrs: attrs || {},
            elems: (attrs ? elems : attrsOrElems) || [],
        };
    };

    module.text = function (text_) {
        return {
            text: text_,
        };
    };

    module.href = function (hashParams, params, path) {
        hashParams = module.encodeParams(hashParams);
        params = module.encodeParams(params);
        path = path ? path : window.location.pathname;
        if (hashParams === null && params === null) {
            return path + '#';
        } else if (hashParams === null && params !== null) {
            return path + '?' + params;
        } else if (hashParams !== null && params === null) {
            return path + '#' + hashParams;
        }
        return path + '?' + params + '#' + hashParams;
    };

    module.encodeParams = function (params) {
        let items = [];
        if (undefined !== params) {
            let name;
            for (name in params) {
                if (params[name] !== null) {
                    items.push(encodeURIComponent(name) + '=' + encodeURIComponent(params[name]));
                }
            }
            for (name in params) {
                if (params[name] === null) {
                    items.push(encodeURIComponent(name));
                }
            }
        }
        return items.length ? items.join('&') : null;
    };

    module.decodeParams = function (paramString) {
        let params = {},
            r = /([^&;=]+)=?([^&;]*)/g,
            d = function (s) { return decodeURIComponent(s.replace(/\+/g, " ")); },
            q = (paramString || window.location.hash.substring(1)),
            e;

        while ((e = r.exec(q)) !== null) {
            params[d(e[1])] = d(e[2]);
        }

        return params;
    };

    module.xhr = function (method, url, async, args) {
        args = args || {};
        let xhr_ = new XMLHttpRequest();
        xhr_.open(method, module.href(null, args.params, url), async);
        xhr_.responseType = args.responseType || 'json';
        xhr_.onreadystatechange = function () {
            if (XMLHttpRequest.DONE === xhr_.readyState) {
                if (200 === xhr_.status) {
                    if (args.onok) {
                        args.onok(xhr_.response);
                    }
                } else {
                    if (args.onerror) {
                        args.onerror(xhr_.response);
                    }
                }
            }
        };
        xhr_.send();
    };

    module.isArray = function (obj) {
        return Object.prototype.toString.call(obj) === '[object Array]';
    }

    module.isObject = function (obj) {
        return Object.prototype.toString.call(obj) === '[object Object]';
    }

    return module;
}());
