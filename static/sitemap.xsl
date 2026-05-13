<?xml version="1.0" encoding="UTF-8"?>

<xsl:stylesheet
version="1.0"
xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
xmlns:sm="http://www.sitemaps.org/schemas/sitemap/0.9">

<xsl:template match="/">

<html>

<head>

<title>Vita₹thi Sitemap</title>

<style>

body{
    font-family:Arial,sans-serif;
    background:#f8fafc;
    margin:0;
    padding:40px;
    color:#111827;
}

.wrap{
    max-width:1100px;
    margin:auto;
}

h1{
    font-size:42px;
    margin-bottom:10px;
}

.sub{
    color:#6b7280;
    margin-bottom:35px;
}

.card{
    background:#fff;
    border-radius:16px;
    padding:20px;
    margin-bottom:18px;
    border:1px solid #e5e7eb;
}

.link{
    color:#2563eb;
    text-decoration:none;
    font-size:17px;
    word-break:break-all;
}

.meta{
    margin-top:10px;
    font-size:14px;
    color:#6b7280;
}

</style>

</head>

<body>

<div class="wrap">

<h1>Vita₹thi Sitemap</h1>

<div class="sub">
All indexed URLs of Vita₹thi
</div>

<!-- INDEX -->
<xsl:for-each select="//sm:sitemap">

<div class="card">

<a class="link">
<xsl:attribute name="href">
<xsl:value-of select="sm:loc"/>
</xsl:attribute>

<xsl:value-of select="sm:loc"/>
</a>

<div class="meta">
Last Modified:
<xsl:value-of select="sm:lastmod"/>
</div>

</div>

</xsl:for-each>

<!-- URLS -->
<xsl:for-each select="//sm:url">

<div class="card">

<a class="link">
<xsl:attribute name="href">
<xsl:value-of select="sm:loc"/>
</xsl:attribute>

<xsl:value-of select="sm:loc"/>
</a>

<div class="meta">

Priority:
<xsl:value-of select="sm:priority"/>

<xsl:if test="sm:lastmod">
 | Updated:
<xsl:value-of select="sm:lastmod"/>
</xsl:if>

</div>

</div>

</xsl:for-each>

</div>

</body>

</html>

</xsl:template>

</xsl:stylesheet>