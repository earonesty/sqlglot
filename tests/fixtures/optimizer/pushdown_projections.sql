SELECT a FROM (SELECT * FROM x);
SELECT _q_0.a AS a FROM (SELECT x.a AS a FROM x AS x) AS _q_0;

SELECT 1 FROM (SELECT * FROM x) WHERE b = 2;
SELECT 1 AS _col_0 FROM (SELECT x.b AS b FROM x AS x) AS _q_0 WHERE _q_0.b = 2;

SELECT (SELECT c FROM y WHERE q.b = y.b) FROM (SELECT * FROM x) AS q;
SELECT (SELECT y.c AS c FROM y AS y WHERE q.b = y.b) AS _col_0 FROM (SELECT x.b AS b FROM x AS x) AS q;

SELECT a FROM x JOIN (SELECT b, c FROM y) AS z ON x.b = z.b;
SELECT x.a AS a FROM x AS x JOIN (SELECT y.b AS b FROM y AS y) AS z ON x.b = z.b;

SELECT x1.a FROM (SELECT * FROM x) AS x1, (SELECT * FROM x) AS x2;
SELECT x1.a AS a FROM (SELECT x.a AS a FROM x AS x) AS x1, (SELECT 1 AS _ FROM x AS x) AS x2;

SELECT x1.a FROM (SELECT * FROM x) AS x1, (SELECT * FROM x) AS x2;
SELECT x1.a AS a FROM (SELECT x.a AS a FROM x AS x) AS x1, (SELECT 1 AS _ FROM x AS x) AS x2;

SELECT a FROM (SELECT DISTINCT a, b FROM x);
SELECT _q_0.a AS a FROM (SELECT DISTINCT x.a AS a, x.b AS b FROM x AS x) AS _q_0;

SELECT a FROM (SELECT a, b FROM x UNION ALL SELECT a, b FROM x);
SELECT _q_0.a AS a FROM (SELECT x.a AS a FROM x AS x UNION ALL SELECT x.a AS a FROM x AS x) AS _q_0;

WITH t1 AS (SELECT x.a AS a, x.b AS b FROM x UNION ALL SELECT z.b AS b, z.c AS c FROM z) SELECT a, b FROM t1;
WITH t1 AS (SELECT x.a AS a, x.b AS b FROM x AS x UNION ALL SELECT z.b AS b, z.c AS c FROM z AS z) SELECT t1.a AS a, t1.b AS b FROM t1;

SELECT a FROM (SELECT a, b FROM x UNION SELECT a, b FROM x);
SELECT _q_0.a AS a FROM (SELECT x.a AS a, x.b AS b FROM x AS x UNION SELECT x.a AS a, x.b AS b FROM x AS x) AS _q_0;

WITH y AS (SELECT * FROM x) SELECT a FROM y;
WITH y AS (SELECT x.a AS a FROM x AS x) SELECT y.a AS a FROM y;

WITH z AS (SELECT * FROM x), q AS (SELECT b FROM z) SELECT b FROM q;
WITH z AS (SELECT x.b AS b FROM x AS x), q AS (SELECT z.b AS b FROM z) SELECT q.b AS b FROM q;

WITH z AS (SELECT * FROM x) SELECT a FROM z UNION SELECT a FROM z;
WITH z AS (SELECT x.a AS a FROM x AS x) SELECT z.a AS a FROM z UNION SELECT z.a AS a FROM z;

SELECT b FROM (SELECT a, SUM(b) AS b FROM x GROUP BY a);
SELECT _q_0.b AS b FROM (SELECT SUM(x.b) AS b FROM x AS x GROUP BY x.a) AS _q_0;

SELECT b FROM (SELECT a, SUM(b) AS b FROM x ORDER BY a);
SELECT _q_0.b AS b FROM (SELECT x.a AS a, SUM(x.b) AS b FROM x AS x ORDER BY a) AS _q_0;

SELECT x FROM (VALUES(1, 2)) AS q(x, y);
SELECT q.x AS x FROM (VALUES (1, 2)) AS q(x, y);

SELECT x FROM UNNEST([1, 2]) AS q(x, y);
SELECT q.x AS x FROM UNNEST(ARRAY(1, 2)) AS q(x, y);

WITH t1 AS (SELECT cola, colb FROM UNNEST([STRUCT(1 AS cola, 'test' AS colb)]) AS "q"("cola", "colb")) SELECT cola FROM t1;
WITH t1 AS (SELECT q.cola AS cola FROM UNNEST(ARRAY(STRUCT(1 AS cola, 'test' AS colb))) AS "q"("cola", "colb")) SELECT t1.cola AS cola FROM t1;

SELECT x FROM VALUES(1, 2) AS q(x, y);
SELECT q.x AS x FROM (VALUES (1, 2)) AS q(x, y);

SELECT i.a FROM x AS i LEFT JOIN (SELECT a, b FROM (SELECT a, b FROM x)) AS j ON i.a = j.a;
SELECT i.a AS a FROM x AS i LEFT JOIN (SELECT _q_0.a AS a FROM (SELECT x.a AS a FROM x AS x) AS _q_0) AS j ON i.a = j.a;
