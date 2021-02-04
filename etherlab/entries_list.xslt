<xsl:stylesheet xmlns:ns="entries_list_ns" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                extension-element-prefixes="ns" version="1.0"
                exclude-result-prefixes="ns">
    <xsl:output method="xml"/>
    <xsl:variable name="space"
                  select="'                                                                                                                                                                                                        '"/>
    <xsl:param name="autoindent" select="4"/>
    <xsl:param name="min_index"/>
    <xsl:param name="max_index"/>
    <xsl:template match="text()">
        <xsl:param name="_indent" select="0"/>
    </xsl:template>
    <xsl:template match="Device">
        <xsl:param name="_indent" select="0"/>
        <xsl:apply-templates select="Profile/Dictionary/Objects/Object">
            <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
        <xsl:for-each select="RxPdo">
            <xsl:call-template name="pdo_entries">
                <xsl:with-param name="direction" select="'Receive'"/>
            </xsl:call-template>
        </xsl:for-each>
        <xsl:for-each select="TxPdo">
            <xsl:call-template name="pdo_entries">
                <xsl:with-param name="direction" select="'Transmit'"/>
            </xsl:call-template>
        </xsl:for-each>
    </xsl:template>
    <xsl:template match="Object">
        <xsl:param name="_indent" select="0"/>
        <xsl:variable name="index">
            <xsl:value-of select="ns:HexDecValue(Index/text())"/>
        </xsl:variable>
        <xsl:variable name="entry_name">
            <xsl:value-of select="ns:EntryName(Name)"/>
        </xsl:variable>
        <xsl:choose>
            <xsl:when test="$index &gt;= $min_index and $index &lt;= $max_index">
                <xsl:variable name="datatype_name">
                    <xsl:value-of select="Type/text()"/>
                </xsl:variable>
                <xsl:variable name="default_value">
                    <xsl:value-of select="Info/DefaultData/text()"/>
                </xsl:variable>
                <xsl:choose>
                    <xsl:when
                            test="ancestor::Dictionary/child::DataTypes/DataType[Name/text()=$datatype_name][SubItem]">
                        <xsl:apply-templates
                                select="ancestor::Dictionary/child::DataTypes/DataType[Name/text()=$datatype_name][SubItem]">
                            <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
                            <xsl:with-param name="index">
                                <xsl:value-of select="$index"/>
                            </xsl:with-param>
                            <xsl:with-param name="entry_name">
                                <xsl:value-of select="$entry_name"/>
                            </xsl:with-param>
                            <xsl:with-param name="sub_default_value">
                                <xsl:value-of select="Info"/>
                            </xsl:with-param>
                        </xsl:apply-templates>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:variable name="subindex">
                            <xsl:text>0</xsl:text>
                        </xsl:variable>
                        <xsl:variable name="sub_entry_flag">
                            <xsl:text>0</xsl:text>
                        </xsl:variable>
                        <xsl:variable name="entry">
                            <xsl:value-of
                                    select="ns:AddEntry($index, $subindex, $entry_name, $datatype_name, BitSize/text(), Flags/Access/text(), Flags/PdoMapping/text(), $default_value, $sub_entry_flag)"/>
                        </xsl:variable>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:when>
        </xsl:choose>
    </xsl:template>
    <xsl:template match="DataType">
        <xsl:param name="_indent" select="0"/>
        <xsl:param name="index"/>
        <xsl:param name="entry_name"/>
        <xsl:param name="sub_default_value"/>
        <xsl:for-each select="SubItem">
            <xsl:variable name="subindex">
                <xsl:value-of select="ns:HexDecValue(SubIdx/text())"/>
            </xsl:variable>
            <xsl:variable name="subentry_name">
                <xsl:value-of select="$entry_name"/>
                <xsl:text>-</xsl:text>
                <xsl:value-of select="ns:EntryName(DisplayName, Name/text())"/>
            </xsl:variable>
            <xsl:variable name="sub_entry_flag">
                <xsl:text>1</xsl:text>
            </xsl:variable>
            <xsl:variable name="entry">
                <xsl:value-of
                        select="ns:AddEntry($index, $subindex, $subentry_name, Type/text(), BitSize/text(), Flags/Access/text(), Flags/PdoMapping/text(), $sub_default_value, $sub_entry_flag)"/>
            </xsl:variable>
        </xsl:for-each>
    </xsl:template>
    <xsl:template name="pdo_entries">
        <xsl:param name="_indent" select="0"/>
        <xsl:param name="direction"/>
        <xsl:variable name="pdo_index">
            <xsl:value-of select="ns:HexDecValue(Index/text())"/>
        </xsl:variable>
        <xsl:variable name="pdo_name">
            <xsl:value-of select="ns:EntryName(Name)"/>
        </xsl:variable>
        <xsl:for-each select="Entry">
            <xsl:variable name="index">
                <xsl:value-of select="ns:HexDecValue(Index/text())"/>
            </xsl:variable>
            <xsl:choose>
                <xsl:when test="$index &gt;= $min_index and $index &lt;= $max_index">
                    <xsl:variable name="subindex">
                        <xsl:value-of select="ns:HexDecValue(SubIndex/text())"/>
                    </xsl:variable>
                    <xsl:variable name="subentry_name">
                        <xsl:value-of select="ns:EntryName(Name)"/>
                    </xsl:variable>
                    <xsl:variable name="access">
                        <xsl:choose>
                            <xsl:when test="$direction='Transmit'">
                                <xsl:text>ro</xsl:text>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:text>wo</xsl:text>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:variable>
                    <xsl:variable name="pdo_mapping">
                        <xsl:choose>
                            <xsl:when test="$direction='Transmit'">
                                <xsl:text>T</xsl:text>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:text>R</xsl:text>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:variable>
                    <xsl:variable name="entry">
                        <xsl:value-of
                                select="ns:AddEntry($index, $subindex, $subentry_name, DataType/text(), BitLen/text(), $access, $pdo_mapping, $pdo_index, $pdo_name, $direction)"/>
                    </xsl:variable>
                </xsl:when>
            </xsl:choose>
        </xsl:for-each>
    </xsl:template>
</xsl:stylesheet>