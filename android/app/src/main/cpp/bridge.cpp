#include <jni.h>
#include <string>
#include "sea_g2p.h"
static std::string utf8(JNIEnv* env, jbyteArray value) {
    jsize size=env->GetArrayLength(value);
    std::string result(size, '\0');
    env->GetByteArrayRegion(value, 0, size, reinterpret_cast<jbyte*>(result.data()));
    return result;
}
static void fail(JNIEnv* env) {
    const char* message=sea_g2p_last_error();
    env->ThrowNew(env->FindClass("java/lang/IllegalStateException"), message ? message : "Chưa mở được bộ phát âm tiếng Việt.");
}
extern "C" JNIEXPORT jlong JNICALL Java_studio_windi_soundbooki_Phonemizer_open(JNIEnv* e,jclass,jbyteArray path) {
    if(sea_g2p_abi_version()!=SEA_G2P_ABI_VERSION) { fail(e); return 0; }
    auto value=utf8(e,path);auto handle=sea_g2p_open(value.c_str());
    if(!handle) fail(e);
    return reinterpret_cast<jlong>(handle);
}
extern "C" JNIEXPORT jbyteArray JNICALL Java_studio_windi_soundbooki_Phonemizer_convert(JNIEnv* e,jclass,jlong handle,jbyteArray text) {
    auto value=utf8(e,text);char* result=sea_g2p_phonemize(reinterpret_cast<sea_g2p*>(handle),value.c_str(),1);
    if(!result) { fail(e); return nullptr; }
    std::string output(result);sea_g2p_string_free(result);
    jbyteArray bytes=e->NewByteArray(output.size());
    e->SetByteArrayRegion(bytes,0,output.size(),reinterpret_cast<const jbyte*>(output.data()));
    return bytes;
}
extern "C" JNIEXPORT void JNICALL Java_studio_windi_soundbooki_Phonemizer_release(JNIEnv*,jclass,jlong handle) { sea_g2p_close(reinterpret_cast<sea_g2p*>(handle)); }
