class RequestHandler {
    handle() {
        console.log("handling request");
    }
}
function initializeApp() {
    return new RequestHandler();
}
