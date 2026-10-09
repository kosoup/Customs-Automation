package kr.kcs.signer;

import com.fasterxml.jackson.annotation.JsonProperty;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;

import javax.xml.crypto.dsig.*;
import javax.xml.crypto.dsig.dom.DOMSignContext;
import javax.xml.crypto.dsig.keyinfo.*;
import javax.xml.crypto.dsig.spec.*;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.*;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.*;
import java.security.cert.X509Certificate;
import java.util.*;
import java.util.logging.Logger;

@SpringBootApplication
@RestController
public class XmlSignerApplication {

    private static final Logger log = Logger.getLogger(XmlSignerApplication.class.getName());

    public static void main(String[] args) {
        SpringApplication.run(XmlSignerApplication.class, args);
    }

    // ── 헬스체크 ────────────────────────────────────────────────────────────
    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok", "service", "KCS XML Signer");
    }

    // ── 서명 요청 모델 ────────────────────────────────────────────────────────
    public static class SignRequest {
        @JsonProperty("xmlContent")     public String xmlContent;
        @JsonProperty("certAlias")      public String certAlias;
        @JsonProperty("keystorePath")   public String keystorePath;
        @JsonProperty("keystorePassword") public String keystorePassword;
    }

    public static class SignResponse {
        public boolean success;
        public String signedXml;
        public String error;

        public static SignResponse ok(String xml)  { var r = new SignResponse(); r.success = true;  r.signedXml = xml; return r; }
        public static SignResponse err(String msg) { var r = new SignResponse(); r.success = false; r.error = msg;     return r; }
    }

    // ── 서명 엔드포인트 ────────────────────────────────────────────────────────
    @PostMapping("/sign")
    public ResponseEntity<SignResponse> sign(@RequestBody SignRequest req) {
        log.info("서명 요청 수신: alias=" + req.certAlias + ", keystore=" + req.keystorePath);
        try {
            String signedXml = signXml(req.xmlContent, req.keystorePath, req.keystorePassword, req.certAlias);
            log.info("서명 완료");
            return ResponseEntity.ok(SignResponse.ok(signedXml));
        } catch (Exception e) {
            log.severe("서명 실패: " + e.getMessage());
            return ResponseEntity.internalServerError().body(SignResponse.err(e.getMessage()));
        }
    }

    // ── 핵심 서명 로직 ─────────────────────────────────────────────────────────
    private String signXml(String xmlContent, String keystorePath, String keystorePassword, String alias)
            throws Exception {

        // 1. KeyStore 로드 (PKCS#12 / JKS 자동 감지)
        KeyStore keyStore = loadKeyStore(keystorePath, keystorePassword);

        // 2. 개인키 + 인증서 추출
        char[] passChars = keystorePassword.toCharArray();
        PrivateKey privateKey = (PrivateKey) keyStore.getKey(alias, passChars);
        X509Certificate cert  = (X509Certificate) keyStore.getCertificate(alias);

        if (privateKey == null) throw new Exception("alias [" + alias + "]에 해당하는 개인키가 없습니다.");
        if (cert == null)       throw new Exception("alias [" + alias + "]에 해당하는 인증서가 없습니다.");

        // 3. XML 파싱
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setNamespaceAware(true);
        var doc = dbf.newDocumentBuilder()
                     .parse(new ByteArrayInputStream(xmlContent.getBytes("UTF-8")));

        // 4. XMLSignatureFactory 초기화
        XMLSignatureFactory fac = XMLSignatureFactory.getInstance("DOM");

        // 5. Reference (서명 대상: 문서 전체)
        Reference ref = fac.newReference(
            "",
            fac.newDigestMethod(DigestMethod.SHA256, null),
            List.of(fac.newTransform(Transform.ENVELOPED, (TransformParameterSpec) null)),
            null, null
        );

        // 6. SignedInfo (RSA-SHA256)
        SignedInfo si = fac.newSignedInfo(
            fac.newCanonicalizationMethod(CanonicalizationMethod.INCLUSIVE, (C14NMethodParameterSpec) null),
            fac.newSignatureMethod(SignatureMethod.RSA_SHA256, null),
            List.of(ref)
        );

        // 7. KeyInfo (인증서 포함)
        KeyInfoFactory kif = fac.getKeyInfoFactory();
        X509Data x509Data = kif.newX509Data(List.of(cert));
        KeyInfo ki = kif.newKeyInfo(List.of(x509Data));

        // 8. XMLSignature 생성 및 서명
        XMLSignature signature = fac.newXMLSignature(si, ki);
        DOMSignContext dsc = new DOMSignContext(privateKey, doc.getDocumentElement());
        signature.sign(dsc);

        // 9. 서명된 XML → String 변환
        Transformer transformer = TransformerFactory.newInstance().newTransformer();
        transformer.setOutputProperty(OutputKeys.ENCODING, "UTF-8");
        transformer.setOutputProperty(OutputKeys.INDENT, "yes");
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        transformer.transform(new DOMSource(doc), new StreamResult(baos));

        return baos.toString("UTF-8");
    }

    private KeyStore loadKeyStore(String path, String password) throws Exception {
        // 확장자로 타입 감지 (p12/pfx → PKCS12, 그 외 → JKS)
        String type = path.toLowerCase().endsWith(".p12") || path.toLowerCase().endsWith(".pfx")
                      ? "PKCS12" : "JKS";

        KeyStore ks = KeyStore.getInstance(type);
        try (InputStream is = Files.newInputStream(Paths.get(path))) {
            ks.load(is, password.toCharArray());
        }
        log.info("KeyStore 로드 완료: type=" + type + ", path=" + path);
        return ks;
    }
}
