<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" 
    xmlns:html="http://www.w3.org/TR/REC-html40"
    xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
    xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:sm="http://www.sitemaps.org/schemas/sitemap/0.9"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    
    <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
    
    <xsl:template match="/">
        <html xmlns="http://www.w3.org/1999/xhtml">
            <head>
                <title>Vita₹thi XML Sitemap</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <style type="text/css">
                    :root {
                        --primary: #4f46e5;
                        --primary-hover: #4338ca;
                        --bg-color: #f8fafc;
                        --text-main: #0f172a;
                        --text-muted: #64748b;
                        --border-color: #e2e8f0;
                    }
                    
                    body {
                        font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        background-color: var(--bg-color);
                        color: var(--text-main);
                        margin: 0;
                        padding: 2rem 1rem;
                        line-height: 1.5;
                    }

                    .wrapper {
                        max-width: 1000px;
                        margin: 0 auto;
                    }

                    .header {
                        text-align: center;
                        margin-bottom: 2.5rem;
                    }

                    .header h1 {
                        font-size: 2.5rem;
                        font-weight: 700;
                        margin: 0 0 0.5rem 0;
                        color: var(--text-main);
                        letter-spacing: -0.025em;
                    }

                    .header p {
                        color: var(--text-muted);
                        font-size: 1.1rem;
                        margin: 0;
                    }

                    .stats {
                        display: inline-block;
                        background-color: #e0e7ff;
                        color: #3730a3;
                        padding: 0.35rem 1rem;
                        border-radius: 9999px;
                        font-size: 0.875rem;
                        font-weight: 600;
                        margin-top: 1rem;
                    }

                    .table-container {
                        background: #ffffff;
                        border-radius: 12px;
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                        overflow: hidden;
                        border: 1px solid var(--border-color);
                    }

                    table {
                        width: 100%;
                        border-collapse: collapse;
                        text-align: left;
                    }

                    thead {
                        background-color: #f1f5f9;
                        border-bottom: 2px solid var(--border-color);
                    }

                    th {
                        padding: 1rem 1.5rem;
                        font-weight: 600;
                        color: var(--text-main);
                        font-size: 0.875rem;
                        text-transform: uppercase;
                        letter-spacing: 0.05em;
                    }

                    td {
                        padding: 1rem 1.5rem;
                        border-bottom: 1px solid var(--border-color);
                        color: var(--text-muted);
                        font-size: 0.95rem;
                        vertical-align: middle;
                    }

                    tr:last-child td {
                        border-bottom: none;
                    }

                    tbody tr {
                        transition: background-color 0.2s ease;
                    }

                    tbody tr:hover {
                        background-color: #f8fafc;
                    }

                    .link {
                        color: var(--primary);
                        text-decoration: none;
                        font-weight: 500;
                        word-break: break-all;
                        transition: color 0.2s ease;
                    }

                    .link:hover {
                        color: var(--primary-hover);
                        text-decoration: underline;
                    }

                    .badge {
                        background: #f1f5f9;
                        color: #475569;
                        padding: 0.25rem 0.6rem;
                        border-radius: 6px;
                        font-size: 0.8rem;
                        font-weight: 600;
                        border: 1px solid #cbd5e1;
                    }

                    @media (max-width: 600px) {
                        th, td {
                            padding: 1rem;
                        }
                        .header h1 {
                            font-size: 2rem;
                        }
                    }
                </style>
            </head>
            <body>
                <div class="wrapper">
                    
                    <div class="header">
                        <h1>Vita₹thi Sitemap</h1>
                        <p>This is the XML Sitemap containing all indexed URLs of Vita₹thi.</p>
                        
                        <!-- URL Counter -->
                        <xsl:if test="count(//sm:sitemap) &gt; 0">
                            <div class="stats">
                                Total Sitemaps: <xsl:value-of select="count(//sm:sitemap)"/>
                            </div>
                        </xsl:if>
                        <xsl:if test="count(//sm:url) &gt; 0">
                            <div class="stats">
                                Total URLs: <xsl:value-of select="count(//sm:url)"/>
                            </div>
                        </xsl:if>
                    </div>

                    <div class="table-container">
                        <table>
                            
                            <!-- SITEMAP INDEX TABLE -->
                            <xsl:if test="count(//sm:sitemap) &gt; 0">
                                <thead>
                                    <tr>
                                        <th>Sitemap URL</th>
                                        <th style="width: 25%;">Last Modified</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <xsl:for-each select="//sm:sitemap">
                                        <tr>
                                            <td>
                                                <a class="link">
                                                    <xsl:attribute name="href">
                                                        <xsl:value-of select="sm:loc"/>
                                                    </xsl:attribute>
                                                    <xsl:value-of select="sm:loc"/>
                                                </a>
                                            </td>
                                            <td>
                                                <xsl:value-of select="concat(substring(sm:lastmod,0,11),concat(' ', substring(sm:lastmod,12,5)))"/>
                                            </td>
                                        </tr>
                                    </xsl:for-each>
                                </tbody>
                            </xsl:if>

                            <!-- STANDARD URL SITEMAP TABLE -->
                            <xsl:if test="count(//sm:url) &gt; 0">
                                <thead>
                                    <tr>
                                        <th>Page URL</th>
                                        <th style="width: 15%;">Priority</th>
                                        <th style="width: 25%;">Last Modified</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <xsl:for-each select="//sm:url">
                                        <tr>
                                            <td>
                                                <a class="link">
                                                    <xsl:attribute name="href">
                                                        <xsl:value-of select="sm:loc"/>
                                                    </xsl:attribute>
                                                    <xsl:value-of select="sm:loc"/>
                                                </a>
                                            </td>
                                            <td>
                                                <xsl:if test="sm:priority">
                                                    <span class="badge"><xsl:value-of select="sm:priority"/></span>
                                                </xsl:if>
                                            </td>
                                            <td>
                                                <xsl:value-of select="concat(substring(sm:lastmod,0,11),concat(' ', substring(sm:lastmod,12,5)))"/>
                                            </td>
                                        </tr>
                                    </xsl:for-each>
                                </tbody>
                            </xsl:if>

                        </table>
                    </div>

                </div>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>