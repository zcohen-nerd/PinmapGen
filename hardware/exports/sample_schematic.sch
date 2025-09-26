<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<eagle version="9.6.2">
<drawing>
<settings>
<setting alwaysvectorfont="no"/>
<setting verticaltext="up"/>
</settings>
<grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" display="no" altdistance="0.01" altunitdist="inch" altunit="inch"/>
<layers>
<layer number="1" name="Top" color="4" fill="1" visible="no" active="no"/>
<layer number="91" name="Nets" color="2" fill="1" visible="yes" active="yes"/>
<layer number="94" name="Symbols" color="4" fill="1" visible="yes" active="yes"/>
</layers>
<schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">
<libraries>
<library name="rp2040">
<packages>
<package name="RP2040-QFN-56">
<description>RP2040 QFN56 Package</description>
</package>
</packages>
<symbols>
<symbol name="RP2040">
<pin name="GP0" x="-15.24" y="12.7" length="short" direction="pas"/>
<pin name="GP1" x="-15.24" y="10.16" length="short" direction="pas"/>
<pin name="GP4" x="-15.24" y="2.54" length="short" direction="pas"/>
<pin name="GP5" x="-15.24" y="0" length="short" direction="pas"/>
<pin name="GP24" x="15.24" y="10.16" length="short" direction="pas" rot="R180"/>
<pin name="GP25" x="15.24" y="7.62" length="short" direction="pas" rot="R180"/>
<pin name="GP26" x="15.24" y="5.08" length="short" direction="pas" rot="R180"/>
<pin name="GP27" x="15.24" y="2.54" length="short" direction="pas" rot="R180"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="RP2040" prefix="U">
<gates>
<gate name="G$1" symbol="RP2040" x="0" y="0"/>
</gates>
<devices>
<device name="" package="RP2040-QFN-56">
<connects>
<connect gate="G$1" pin="GP0" pad="2"/>
<connect gate="G$1" pin="GP1" pad="3"/>
<connect gate="G$1" pin="GP4" pad="6"/>
<connect gate="G$1" pin="GP5" pad="7"/>
<connect gate="G$1" pin="GP24" pad="35"/>
<connect gate="G$1" pin="GP25" pad="36"/>
<connect gate="G$1" pin="GP26" pad="37"/>
<connect gate="G$1" pin="GP27" pad="38"/>
</connects>
</device>
</devices>
</deviceset>
</devicesets>
</library>
</libraries>
<attributes>
</attributes>
<variantdefs>
</variantdefs>
<classes>
<class number="0" name="default" width="0" drill="0">
</class>
</classes>
<parts>
<part name="U1" library="rp2040" deviceset="RP2040" device=""/>
</parts>
<sheets>
<sheet>
<description>Main Sheet</description>
<instances>
<instance part="U1" gate="G$1" x="50.8" y="50.8" smashed="yes"/>
</instances>
<busses>
</busses>
<nets>
<net name="I2C0_SDA" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="GP0"/>
<wire x1="35.56" y1="63.5" x2="25.4" y2="63.5" width="0.1524" layer="91"/>
<label x="25.4" y="63.5" size="1.778" layer="95"/>
</segment>
</net>
<net name="I2C0_SCL" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="GP1"/>
<wire x1="35.56" y1="60.96" x2="25.4" y2="60.96" width="0.1524" layer="91"/>
<label x="25.4" y="60.96" size="1.778" layer="95"/>
</segment>
</net>
<net name="LED_DATA" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="GP4"/>
<wire x1="35.56" y1="53.34" x2="25.4" y2="53.34" width="0.1524" layer="91"/>
<label x="25.4" y="53.34" size="1.778" layer="95"/>
</segment>
</net>
<net name="BUTTON" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="GP5"/>
<wire x1="35.56" y1="50.8" x2="25.4" y2="50.8" width="0.1524" layer="91"/>
<label x="25.4" y="50.8" size="1.778" layer="95"/>
</segment>
</net>
<net name="USB_DP" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="GP24"/>
<wire x1="66.04" y1="60.96" x2="76.2" y2="60.96" width="0.1524" layer="91"/>
<label x="76.2" y="60.96" size="1.778" layer="95"/>
</segment>
</net>
<net name="USB_DN" class="0">
<segment>
<pinref part="U1" gate="G$1" pin="GP25"/>
<wire x1="66.04" y1="58.42" x2="76.2" y2="58.42" width="0.1524" layer="91"/>
<label x="76.2" y="58.42" size="1.778" layer="95"/>
</segment>
</net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>