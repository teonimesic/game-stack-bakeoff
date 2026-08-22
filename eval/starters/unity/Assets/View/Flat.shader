// The one shader the view uses: flat, unlit, no fog, no lighting, no
// pipeline-specific includes. Shipping our own instead of Shader.Find-ing a
// built-in name means the rendered result does not change if Unity retunes a
// stock shader, and the golden image stays meaningful across editor versions.
//
// It is listed in ProjectSettings/GraphicsSettings.asset under
// m_AlwaysIncludedShaders so player builds cannot strip it.
Shader "Starter/Flat"
{
    Properties { _Color ("Color", Color) = (1,1,1,1) }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Pass
        {
            ZWrite On
            Cull Off
            Fog { Mode Off }
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            fixed4 _Color;
            struct v2f { float4 pos : SV_POSITION; };
            v2f vert(appdata_base v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                return o;
            }
            fixed4 frag(v2f i) : SV_Target { return _Color; }
            ENDCG
        }
    }
}
