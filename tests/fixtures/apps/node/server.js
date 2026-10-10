// App mínima para tests/build-fixtures.sh: responde en $PORT.
const http = require("http");
http.createServer((req, res) => res.end("andamio-ok\n")).listen(process.env.PORT || 3000, "0.0.0.0");
